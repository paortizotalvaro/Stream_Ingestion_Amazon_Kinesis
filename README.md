
#### __Copyright notice__
The content of this lab was made available by DeepLearning.AI. You may not use or distribute this code for commercial purposes. <br>
I have added my own modifications to the code for learning purposes. <br>
I added my own extra notes and reorganized the structure of the document for my own future reference

# Assignment: Stream_Ingestion_Amazon_Kinesis

This is the second lab of week 2 of the course Source Systems, Data Ingestion, and Pipelines of DeepLearning.AI in Coursera.
<br>
This lab has two main goals:
1. ork with a Kinesis Data Stream acting as a router between a simple producer and a simple consumer. Using the producer application, you will manually generate data and write it to the Kinesis Data Stream. After that, you will consume the generated data from that stream.

2. Perform a streaming ETL process: you will consume data from a Kinesis Data Stream that is fed by a producer. You will apply some simple transformations to this data, and then put the transformed data into one of two other data streams. From each of these two new data streams, data will be taken by a Kinesis Firehose and delivered to their respective S3 buckets.


# Table of Contents

- [ 1 - THEORY](#1)
  - [ 1.1 - Components of an Event-Streaming Platform](#1-1)
  - [ 1.2 - Shards and iterators](#1-2)
- [ 2 - CREATE A DATA STREAM](#2)
- [ 3 - CONSUMING FROM THE STREAM](#3)
  - [ 3.1  - Understanding consumer_from_cli.py](#3-1)
      - [ a) Parse Stream Name with argparse](#3-a)
      - [ b) fetch_shards_and_iterators()](#3-b)
      - [ c) poll_shards()] (#3-c)
  - [ 3.2 - Running consumer_from_cli.py](#3-2)
- [ 4 - PRODUCE: WRITE TO THE STREAM]
  - [ 4.1 - Understanding producer_from_cli.py](#4-1)
  - [ 4.2 - Running producer_from_cli.py](#4-2)
- [ 5 - IMPLEMENTING A STREAMING ETL PROCESS](#5)
  - [ 5.1 - Creating the Infrastructure for the Streaming ETL Process](#5-1)
  - [ 5.2 - Implementing the Streaming ETL](#5-2)



<a id='1'></a>
# 1 THEORY

<a id='1-1'></a>
## 1.1 - Components of an Event-Streaming Platform

An event-driven architecture consists of

a producer ----> a router (buffer/message broker) ----> a consumer. 

- producer: in the folder `src/cli`, you can find the Python script: `producer_from_cli.py`. This script contains code that writes one record to a Kinesis Data Stream. You will call this script from a command line interface (CLI) and pass in two arguments: the name of the Kinesis Data Stream and a JSON string representing the message record.<br>

- router: you will create a Kinesis Data Stream that will act as a router between a producer and a consumer<br>

- consumer: in the same folder `src/cli`, you can find the Python script: `consumer_from_cli.py` which you will also call from the command line interface (CLI). It takes in one argument which is the name of the Kinesis Data Stream from which the consumer will read the message records.

<a id='1-2'></a>
## 1.2 - Shards and Iterators

- A __shard__ is a uniquely identified sequence of data records in a stream. Each stream consists of one or more shards, which determine the stream’s capacity.

- A __shard iterator__ is a token that tells Kinesis where to start reading data from within a shard. You use it to retrieve records using the GetRecords API. 
  It acts like a pointer that enables you to read data records from a specific position in a shard within a stream.

#### Types of Shard Iterators
When you request a shard iterator, you specify the type, which determines where in the shard the iterator starts:

- TRIM_HORIZON: Start from the oldest available record.
- LATEST: Start from the most recent record (new data only).
- AT_SEQUENCE_NUMBER: Start from a specific sequence number.
- AFTER_SEQUENCE_NUMBER: Start right after a specific sequence number.
- AT_TIMESTAMP: Start from records at or after a specific timestamp.

#### Example Usage

```python
response = kinesis_client.get_shard_iterator(
    StreamName='my-stream',
    ShardId='shardId-000000000000',
    ShardIteratorType='LATEST'
)
shard_iterator = response['ShardIterator']

```





# 2. CREATE A DATA STREAM
<a id='1-1'></a>
### Get the link to the AWS console

For these labs the url is provided to access the AWS console. It can be accessed in the notebook with:

```python

with open('../.aws/aws_console_url', 'r') as file:
    aws_url = file.read().strip()

HTML(f'<a href="{aws_url}" target="_blank">GO TO AWS CONSOLE</a>')
```

<a id='1-2'></a>
### Create the Data Stream
- In the AWS console search for Kinesis, and click on Create data stream. 
- Name it `de-c2w2lab1-kinesis-data-stream-cli` and leave the rest as default. 
- Click on Create data stream button. Once it is in Active status you can continue with the next steps.


<a id='3'></a>
# 3. CONSUMING FROM THE STREAM

<a id='3-1'></a>
## 3.1 Understanding consumer_from_cli.py

<a id='3-a'></a>
### a) Parse Stream Name with argparse
Outside of the main, create a new argument object called parser and add to it the argument "stream":

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--stream", type=str, help="Kinesis data stream name")

```
The argparse module is used for parsing command-line arguments. <br>
It allows you to run your script from the terminal and pass in options like --stream my-stream-name.
1. `import argparse`
This imports Python’s built-in argparse module, which is used for parsing command-line arguments. It allows you to run your script from the terminal and pass in options like --stream my-stream-name.

2. `parser = argparse.ArgumentParser()`
This creates a new argument parser object. Think of it as a tool that knows how to read and interpret command-line arguments.
You can optionally pass a description here: `argparse.ArgumentParser(description="My script description")`


3. `parser.add_argument("--stream", type=str, help="Kinesis data stream name")`
This tells the parser to expect a command-line argument called --stream.
--stream: The name of the argument (used like --stream my-stream-name)
type=str: The value passed must be a string.
help="...": This is a description that shows up when you run the script with --help.


Then, inside of the `main()`, the name of the stream is obtained by:

```python
    args = parser.parse_args()

    kinesis_stream_name = args.stream
```

<a id='3-b'></a>
### b) fetch_shards_and_iterators()

This function 
- iterates over all shards in the stream and retrieves their iterators with type "TRIM_HORIZON"
- It stores the shard IDs and iterators in a list of objects of the class ShardIteratorPair class.

#### class ShardIteratorPair
Data container class representing a pair of a shard ID and its corresponding shard iterator.

Additional note: to view the values in the pairs, a `__repr__` method can be added:

```python

class ShardIteratorPair:
    def __init__(self, shard_id, iterator):
        self.shard_id = shard_id
        self.iterator = iterator

    def __repr__(self):
        return f"ShardIteratorPair(shard_id='{self.shard_id}', iterator='{self.iterator[:10]}...')"

```

The printing object would give something like:

```python
ShardIteratorPair(shard_id='shardId-000000000001', iterator='AAAAAAAAAA...')
```


<a id='3-c'></a>
### c) poll_shards()
the poll_shards function continuously reads records from Kinesis shards:

- Decodes and logs each record.
- Updates shard iterators to maintain progress.
- Handles errors gracefully.
- Sleeps briefly between polling cycles.



<a id='3-2'></a>
### 3.2 Running consumer_from_cli.py

#### First run of the script
This consumer script iterates through all the shards of the data stream, reading all the records from each shard and printing some information about each record in the terminal. 

The consumer script expects one argument (the name of the data stream) which is specified using the --stream flag followed by the data stream name. 
To execute this python script run

```bash
cd src/cli/
python consumer_from_cli.py --stream de-c2w2lab1-kinesis-data-stream-cli
```

In this first run nothing will now appear even after waiting for 1 or 2 minutes. This is because the script is consuming from a data stream that is currently empty.





<a id='4'></a>
# 4.0PRODUCE: WRITE TO THE STREAM

<a id='4-1'></a>
## 4.1 Understanding producer_from_cli.py
The script sends a single JSON-formatted record to an Amazon Kinesis data stream using command-line arguments.

Workflow:
1. Parse command-line arguments.
2. Convert the JSON string to a Python dictionary.
3. Send the record to the specified Kinesis stream using put_record().
4. Use the session_id from the JSON as the partition key.
5. Log the result or any errors.

### kinesis.put_record()
This script uses kinesis.put_record(). <br>
The kinesis.put_record() method in the Boto3 AWS SDK for Python is used to send a single data record into an Amazon Kinesis Data Stream.<br>
Basic syntax:
```python
response = kinesis.put_record(
    StreamName='your-stream-name',
    Data=b'your-data-bytes',
    PartitionKey='your-partition-key'
)
```
- StreamName (str):
  The name of the Kinesis stream you're writing to.

- Data (bytes or bytearray):
  The actual data payload. It must be in bytes, so if you're sending a string or JSON, you need to encode it first.

- PartitionKey (str):
  A string used to determine which shard the data record is assigned to. Records with the same partition key go to the same shard (unless the shard is split). <br>
  
  You create the partition key yourself when you call put_record() in Kinesis. It is not pre-defined by AWS or the stream.
          - The partition key is a logical grouping mechanism that you control.
          - It determines how records are distributed across shards and how ordering is preserved within a shard.
  - You typiAWS Kinesis does not enforce or suggest any specific partition key — it’s entirely up to your application logic.cally choose a partition key based on a field in your data that:
          - Groups related records together
          - Ensures even distribution across shards

  - Why It Matters
          - Records with the same partition key go to the same shard, preserving order.
          - Choosing a diverse set of keys helps balance load across shards.

          
<a id='4-2'></a>
## 4.2 Running producer_from_cli.py

```bash
cd src/cli/
python producer_from_cli.py --stream de-c2w2lab1-kinesis-data-stream-cli --json_string '{"session_id": "a1", "customer_number": 100, "city": "Washington", "country": "USA", "credit_limit": 1000, "browse_history": [ {"product_code": "Product1", "quantity": 2, "in_shopping_cart": true}, {"product_code": "Product2", "quantity": 1, "in_shopping_cart": false}]}'
```


<a id='5'></a>
# 5. IMPLEMENTING A STREAMING ETL PROCESS

Consumer-side infrastructure of a streaming ETL pipeline for an e-commerce event-streaming scenario.<br>
The producer and the initial Kinesis Data Stream are already provided.

Data Source
- The incoming data contains browsing history from the e-commerce site.
- Each record includes city and country information, which you'll use to determine the customer's location.
Example: 

```json
{
    "session_id": "a1",
    "customer_number": 100,
    "city": "Washington",
    "country": "USA",
    "credit_limit": 1000,
    "browse_history": [
        {
            "product_code": "Product1",
            "quantity": 2,
            "in_shopping_cart": true
        },
        {
            "product_code": "Product2",
            "quantity": 1,
            "in_shopping_cart": false
        }
    ]
}
```

Objectives
- Ingest data from a source Kinesis Data Stream.
- Apply a simple transformation to the data.
- Route the transformed data to one of two destination Kinesis Data Streams based on some logic.
      Customer behavior varies by country, especially between USA and International customers. To support country-specific recommendation engines, you need to route and store data separately based on customer location.
            - Inspect each record's country field.
            - If country == "USA" → route to USA stream.
            - Else → route to International stream.
- Each destination stream is connected to a Kinesis Firehose, which delivers the data to its respective Amazon S3 bucket for storage and analysis.

Infrastructure Components to Create (using boto3)
- Two Kinesis Data Streams – for routing transformed data.
- Two Kinesis Firehose Delivery Streams – to move data from Kinesis to S3.
- Two S3 Buckets – to store the final transformed data.

**Why Two Data Streams?**
Using multiple data streams allows for data segregation based on transformation logic or business rules. This enables:
- Easier downstream processing.
- Better scalability and fault isolation.
- More targeted analytics.




<a id='5-1'></a>
## 5.1. Creating the Infrastructure for the Streaming ETL Process

### a) Define account ID and region
```python
ACCOUNT_ID = subprocess.run(['aws', 'sts', 'get-caller-identity', '--query', 'Account', '--output', 'text'], capture_output=True, text=True).stdout.strip()
AWS_DEFAULT_REGION = 'us-east-1'
```

The subprocess module in Python is used to spawn new processes, connect to their input/output/error pipes, and obtain their return codes. It's a powerful tool for running shell commands or external programs from within a Python script.

``` python
import subprocess

subprocess.run(
    ['aws', 'sts', 'get-caller-identity', '--query', 'Account', '--output', 'text'],
    capture_output=True,
    text=True
).stdout.strip()

```

- aws sts get-caller-identity: Gets details about the IAM identity used to make the request.
- --query 'Account': Filters the output to show only the AWS account ID.
- --output text: Returns the result as plain text (not JSON).
- capture_output=True: Captures the command's output.
- text=True: Ensures the output is returned as a string (not bytes).
- .stdout.strip(): Removes any leading/trailing whitespace or newlines.


### b) Create S3 buckets
The two buckets follow this naming convention:
- USA: `de-c2w2lab1-{ACCOUNT_ID}-usa`
- International: `de-c2w2lab1-{ACCOUNT_ID}-international`


```python
import boto3

USA_BUCKET = f'de-c2w2lab1-{ACCOUNT_ID}-usa'
INTERNATIONAL_BUCKET = f'de-c2w2lab1-{ACCOUNT_ID}-int'


def create_s3_bucket(bucket_name: str, region: str) -> None:
   # Call the boto3 client with the `'s3'` resource and region. 
    s3_client = boto3.client('s3', region_name=region)
    
    # Create the S3 bucket
    try:
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"S3 bucket '{bucket_name}' created successfully in region '{region}'.")
    except Exception as e:
        print(f"An error occurred: {e}")


# Create the USA bucket
create_s3_bucket(bucket_name=USA_BUCKET, region=AWS_DEFAULT_REGION)
    
# Create the international bucket
create_s3_bucket(bucket_name=INTERNATIONAL_BUCKET, region=AWS_DEFAULT_REGION)


```

Expected output:
```bash
S3 bucket 'de-c2w2lab1-627657969326-usa' created successfully in region 'us-east-1'.
S3 bucket 'de-c2w2lab1-627657969326-int' created successfully in region 'us-east-1'.
```

To check if the buckets exist with python:

```Python
!aws s3 ls
```

### c) Create two Kinesis Data Streams
Both streams should have a shard count of 2, meaning 2 partitions per stream, and should be named with the following convention:
   - USA: `de-c2w2lab1-usa-data-stream`
   - International: `de-c2w2lab1-international-data-stream`

```python
USA_DATA_STREAM = 'de-c2w2lab1-usa-data-stream'
INTERNATIONAL_DATA_STREAM = 'de-c2w2lab1-international-data-stream'

def create_kinesis_data_stream(stream_name: str, shard_count: int = 2) -> None:
    # Call the boto3 client with the `kinesis` resource.  Store the object in `client`.
    client = boto3.client("kinesis")

    # Check if the stream already exists
    if stream_name in client.list_streams()["StreamNames"]:
        print(f"Kinesis data stream {stream_name} already exists")
        return
    
    # Use the `create_stream()` method from the client and pass the data stream name and the shard count.
    response = client.create_stream(StreamName=stream_name, ShardCount=shard_count)
    print("Kinesis data stream created:", response)


# Create the USA data stream
create_kinesis_data_stream(stream_name=USA_DATA_STREAM, shard_count=2)

# Create the International data stream
create_kinesis_data_stream(stream_name=INTERNATIONAL_DATA_STREAM, shard_count=2)

```

Expected response
```bash
Kinesis data stream created: {'ResponseMetadata': {'RequestId': 'e107c00c-0d68-d008-81f6-58a7544e087c', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': 'e107c00c-0d68-d008-81f6-58a7544e087c', 'x-amz-id-2': 'G2dxa8Mav7BS123DF3s9ZKPjbEDEL9Djhf9HeaGTb/RxM2OnA3CEhAFJ9PXYDfoOiWP/lQ8Qbn25NvqLPCGFMHgvvj+SECav', 'date': 'Wed, 16 Jul 2025 12:09:15 GMT', 'content-type': 'application/x-amz-json-1.1', 'content-length': '0', 'connection': 'keep-alive'}, 'RetryAttempts': 0}}
Kinesis data stream created: {'ResponseMetadata': {'RequestId': 'c2522b3f-910d-d3ba-a2a3-b3947339c0c0', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': 'c2522b3f-910d-d3ba-a2a3-b3947339c0c0', 'x-amz-id-2': 'i19f0jE4lAIMgllRuJqqm3BvOLUITmF/BdNK0c135aFIh9d847ypJbI9K8SfXpFcN8UF112m0wfUrDL8u41XDggnQfHpVhJU', 'date': 'Wed, 16 Jul 2025 12:09:16 GMT', 'content-type': 'application/x-amz-json-1.1', 'content-length': '0', 'connection': 'keep-alive'}, 'RetryAttempts': 0}}
```

#### Check the status of the resources
```python
def is_stream_ready(stream_name: str) -> None:
    client = boto3.client("kinesis")
    response = client.describe_stream(StreamName=stream_name)
    return response["StreamDescription"]["StreamStatus"] == "ACTIVE"

# Check if the streams are ready
print(is_stream_ready(stream_name=USA_DATA_STREAM))
print(is_stream_ready(stream_name=INTERNATIONAL_DATA_STREAM))
```


### d) Create two Kinesis Firehose Instances

``` python
def create_kinesis_firehose( 
    firehose_name: str, 
    stream_name: str, 
    bucket_name: str, 
    role_name: str, 
    log_group: str, 
    log_stream:str, 
    account_id: int, 
    region: str):

    # Call the boto3 client with the firehose resource. Assign it to the client variable.
    client = boto3.client("firehose")

    # Check if firehose stream already exists
    if firehose_name in client.list_delivery_streams()["DeliveryStreamNames"]:
        print(f"Kinesis firehose stream {firehose_name} already exists.")
        return
    
    # Use the create_delivery_stream() method of the client object.
    response = client.create_delivery_stream(
        # Pass the firehose name.
        DeliveryStreamName=firehose_name,
        # Specify that the delivery stream uses a Kinesis data stream as a source.
        DeliveryStreamType='KinesisStreamAsSource',
        # Configure the S3 as the destination.
        S3DestinationConfiguration={
            # The ARN of the IAM role that Firehose will assume to access S3 and other services.
            "RoleARN": f"arn:aws:iam::{account_id}:role/{role_name}",
            # The ARN of the S3 bucket where data will be stored.
            "BucketARN": f"arn:aws:s3:::{bucket_name}",
            # The folder path prefix for delivered data in the S3 bucket.
            "Prefix": "firehose/",
            # Prefix for storing error records in S3.
            "ErrorOutputPrefix": "errors/",
            # Controls how Firehose buffers incoming data before writing to S3 (max size/time)
            "BufferingHints": {"SizeInMBs": 1, "IntervalInSeconds": 60},
            "CompressionFormat": "UNCOMPRESSED",  
            "CloudWatchLoggingOptions": {
                "Enabled": True,
                "LogGroupName": log_group, 
                "LogStreamName": log_stream
            },
            # control encription settings
            "EncryptionConfiguration": {"NoEncryptionConfig": "NoEncryption"},
        },
        # Configure the Kinesis Stream as the Source.
        KinesisStreamSourceConfiguration={
            "KinesisStreamARN": f"arn:aws:kinesis:{region}:{account_id}:stream/{stream_name}",
            "RoleARN": f"arn:aws:iam::{account_id}:role/{role_name}",
        },
    )
    
    print("Kinesis Firehose created:", response)


# Create the delivery stream for USA orders.
create_kinesis_firehose(firehose_name='de-c2w2lab1-firehose-usa', 
                        stream_name=USA_DATA_STREAM,
                        bucket_name=USA_BUCKET,
                        role_name='de-c2w2lab1-firehose-role', 
                        log_group='de-c2w2lab1-firehose-usa-log-group', 
                        log_stream='de-c2w2lab1-usa-firehose-log-stream', 
                        account_id=ACCOUNT_ID, 
                        region=AWS_DEFAULT_REGION 
                       )

# Create the delivery stream for International orders.
create_kinesis_firehose(firehose_name='de-c2w2lab1-firehose-international', 
                        stream_name=INTERNATIONAL_DATA_STREAM,
                        bucket_name=INTERNATIONAL_BUCKET,
                        role_name='de-c2w2lab1-firehose-role', 
                        log_group='de-c2w2lab1-firehose-international-log-group', 
                        log_stream='de-c2w2lab1-international-firehose-log-stream', 
                        account_id=ACCOUNT_ID, 
                        region=AWS_DEFAULT_REGION 
                       )


```



This function makes use of the `boto3` client method [create_delivery_stream()](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/firehose/client/create_delivery_stream.html). The arguments passed into this method include:
  - the source, source: Kinesis Data Stream
  - and destination for the Kinesis Firehose, destination: S3 bucket
  - The role name passed into the configuration of the source and destination, represents the role that will be attached to the Kinesis Firehose to allow it to read from a Kinesis Data Stream and write to an S3 bucket. <br>
  Note that `arn` means Amazon resource name and it is used to uniquely identify AWS resources, you can learn more about it [here](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference-arns.html#arn-syntax-kinesis-streams). 

Once these resources are configured, Kinesis Firehose will be able to automatically read from the Kinesis Data Stream and automatically write to the S3 bucket. 


Expected output:
```bash
Kinesis Firehose created: {'DeliveryStreamARN': 'arn:aws:firehose:us-east-1:627657969326:deliverystream/de-c2w2lab1-firehose-usa', 'ResponseMetadata': {'RequestId': 'e7b2f74a-0160-0d91-874a-eb5a5bee106f', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': 'e7b2f74a-0160-0d91-874a-eb5a5bee106f', 'x-amz-id-2': '/KImT3AYyvw+UImlspmESukSzZQ1uC/96fLTPFoZicDpF1Y5TwYpAQxQQgUr9LcbOZIXbnA2lxpIj3+jiunGQPZOXKTopZ5E', 'content-type': 'application/x-amz-json-1.1', 'content-length': '103', 'date': 'Mon, 21 Jul 2025 10:43:28 GMT'}, 'RetryAttempts': 0}}
Kinesis Firehose created: {'DeliveryStreamARN': 'arn:aws:firehose:us-east-1:627657969326:deliverystream/de-c2w2lab1-firehose-international', 'ResponseMetadata': {'RequestId': 'c695f69a-e480-b3ee-a66d-ea8ad2d1dd1a', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': 'c695f69a-e480-b3ee-a66d-ea8ad2d1dd1a', 'x-amz-id-2': 'yTFqkksR8Sa9y52sRMxYCazEP6ohU+7Eo/5gRqvFWRvgo/S/tEOnOplXlV09Np3nt5CXpmjcN+Wh2B0nXFL91dxf8sM74/Jf', 'content-type': 'application/x-amz-json-1.1', 'content-length': '113', 'date': 'Mon, 21 Jul 2025 10:43:29 GMT'}, 'RetryAttempts': 0}}
```



<a id='5-2'></a>
## 5.2. Implementing the Streaming ETL Process

- The producer generates data dynamically with an average mean time between records of 10 seconds, that should be taken into account when consuming the data and when visualizing it. 

- During the consumption, there are some simple transformations over the records before sending them to the new data streams created with `boto3`. The transformation will consist of adding 4 additional attributes.


### consumer.py
Execute the consumer with the following command:

```bash
cd src/etl
python consumer.py --source_stream de-c2w2lab1-kinesis-data-stream --dest_streams '{"USA": "de-c2w2lab1-usa-data-stream", "International": "de-c2w2lab1-international-data-stream"}'
```

By running this command, the producer will send records to the Kinesis Data Stream. This consumer script will read those records, transform them and then send them to the appropriate Kinesis streams. The Kinesis Firehose will finally automatically deliver the data to the S3 buckets. 

*Note*: This command will run continuously, so as long as you don't exit the terminal, records will continue to be streamed.


#### Check the destination streams
To check the usa or the international destination stream, use another terminal. Use the consumer of the first part of the lab located at `src/cli/consumer_from_cli.py` to read from either the USA or International data stream to inspect visually your transformed data.

```bash
cd src/cli/
python consumer_from_cli.py --stream de-c2w2lab1-usa-data-stream
```
Finally, you can inspect from the AWS console each of the S3 buckets to see when the data was saved (you can find the link to the AWS console in step 1.1). This process can take around 5-7 minutes to start seeing any file in the S3 bucket after the transformations are sent to the data streams. 

