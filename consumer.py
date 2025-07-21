import argparse
import datetime
import json
import logging
import sys
import time

import boto3

logging.basicConfig(
    format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("consumer.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

parser = argparse.ArgumentParser()
parser.add_argument(
    "--source_stream", type=str, help="Kinesis data stream name"
)
parser.add_argument(
    "--dest_streams",
    type=str,
    help="JSON Object as string with only two keys: 'USA' and 'International'.",
)

#  convert a datetime object into a format that can be serialized into JSON,
# which doesn't natively support datetime objects.
def serialize_datetime(json_obj):
    
    #  check if the input json_obj is an instance of the datetime.datetime class
    # isinstance() is a built-in function that returns True if the object is of the specified type.    
    if isinstance(json_obj, datetime.datetime):
        
        # If the object is a datetime, convert it to an ISO 8601 formatted string
        # This format is widely used and JSON-friendly, e.g., "2025-07-16T14:26:10".
        return json_obj.isoformat()
    raise TypeError("Type not serializable")


class ShardIteratorPair:
    """Data container class used to store information about shards
    and their iterators.
    """
    def __init__(self, shard_id, iterator):
        self.shard_id = shard_id
        self.iterator = iterator


def fetch_shards_and_iterators(kinesis, source_stream_name):
    """This function retrieves a list of shard iterators for the specified
    Kinesis stream. It iterates over all shards in the stream, retrieves
    their iterators using "TRIM_HORIZON" as the iterator type (which starts
    reading from the oldest available data in the shard), and stores the shard
    ID and iterator in a list of ShardIteratorPairs. It handles pagination if
    the number of shards exceeds the limit returned by the API.

    Args:
        kinesis (boto3 client): Boto3 client for kinesis resources
        stream_name (str): Kinesis data stream name

    Returns:
        List: Pair of ShardId and corresponding Iterator
    """
    shard_iterators = []
    response_shards = kinesis.list_shards(StreamName=source_stream_name)
    while response_shards["Shards"]:
        for shard in response_shards["Shards"]:
            shard_id = shard["ShardId"]
            itr_response = kinesis.get_shard_iterator(
                StreamName=source_stream_name,
                ShardId=shard_id,
                ShardIteratorType="TRIM_HORIZON",
            )
            shard_itr = ShardIteratorPair(
                shard_id, itr_response["ShardIterator"]
            )
            shard_iterators.append(shard_itr)

        # Check if there's a NextToken in the response,
        # indicating more shards to fetch.
        # Use the NextToken to fetch the next page of shards
        if "NextToken" in response_shards:
            response_shards = kinesis.list_shards(
                StreamName=source_stream_name,
                NextToken=response_shards["NextToken"],
            )
        else:
            break

    return shard_iterators


def transform_stream():
    """
    This is a placeholder function:
    The pass statement is a no-operation placeholder.
    It tells Python: “Do nothing here—for now.”
    It's often used when you're planning to implement the function later, 
    but want your code to run without errors in the meantime.
    """
    pass


def poll_shards(kinesis, shard_iterators, kinesis_dest_stream_names):

    # start an infinite loop to continuously poll data from the shards
    while True:
        for shard_itr in shard_iterators:
            try:
                records_response = kinesis.get_records(
                    ShardIterator=shard_itr.iterator, Limit=200
                )
                for record in records_response["Records"]:
                    user_session = json.loads(record["Data"].decode("utf-8"))
                    logging.info(
                        f"Read User Session {user_session} from Shard {shard_itr.shard_id} at position {record['SequenceNumber']}"
                    )


                    # Performing small transformation and putting record into a new kinesis data stream
                    try:
                        # Add new attribute: processing_timestamp, containing the current time
                        user_session[
                            "processing_timestamp"
                        ] = datetime.datetime.now()

                        # Initialize counters of total number of products and in cart
                        overall_product_quantity = 0
                        overall_in_shopping_cart = 0

                        for product in user_session["browse_history"]:
                            # Count the total number of product quantities in browse history
                            overall_product_quantity += int(
                                product["quantity"]
                            )

                            # Count the number of products in the shopping cart
                            if product["in_shopping_cart"] is True:
                                overall_in_shopping_cart += int(
                                    product["quantity"]
                                ) 

                        # Add values to new attributes
                        user_session[
                            "overall_product_quantity"
                        ] = overall_product_quantity
                        user_session[
                            "overall_in_shopping_cart"
                        ] = overall_in_shopping_cart

                        user_session["total_different_products"] = len(
                            user_session["browse_history"]
                        )
                        
                        # execute single PutRecord request
                        response = kinesis.put_record(
                            StreamName=kinesis_dest_stream_names["USA"]
                            if user_session["country"] == "USA"
                            else kinesis_dest_stream_names[
                                "International"
                            ],

                            Data=json.dumps(
                                user_session, default=serialize_datetime
                            ).encode("utf-8"),
                            PartitionKey=user_session["session_id"],
                        )
                        logging.info(f"Processed User Session {user_session}")
                        logging.info(
                            f"Produced record {response['SequenceNumber']} to Shard {response['ShardId']}\n\n"
                        )
                    
                    
                    except Exception as e:
                        logging.error(
                            {
                                "message": "Error producing record",
                                "error": str(e),
                                "record": user_session,
                            }
                        )

                if records_response["NextShardIterator"]:
                    shard_itr.iterator = records_response["NextShardIterator"]
            except Exception as e:
                logging.error(
                    {"message": "Failed fetching records", "error": str(e)}
                )

        # Adding small delay just to visualization purposes
        time.sleep(2)


def main():
    logging.info("Starting GetRecords Consumer")
    args = parser.parse_args()

    kinesis_source_stream_name = args.source_stream
    kinesis_dest_stream_names = json.loads(args.dest_streams)

    kinesis = boto3.client("kinesis")

    shard_iterators = fetch_shards_and_iterators(
        kinesis, kinesis_source_stream_name
    )
    poll_shards(kinesis, shard_iterators, kinesis_dest_stream_names)


if __name__ == "__main__":
    main()
