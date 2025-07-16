
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
  - [ 4.1  - Understanding producer_from_cli.py](#3-1)
      - [ a) ](#3-a)
      - [ b) ](#3-b)
      - [ c) ] (#3-c)
  - [ 4.2 - Running producer_from_cli.py](#3-2)
- [ 5 - IMPLEMENTING A STREAMING ETL PROCESS](#2)
  - [ 2.1 - Creating the Infrastructure for the Streaming ETL Process](#2-1)
  - [ 2.2 - Implementing the Streaming ETL](#2-2)



<a id='1'></a>
## 1 THEORY

<a id='1-1'></a>
### 1.1 - Components of an Event-Streaming Platform

An event-driven architecture consists of

a producer ----> a router (buffer/message broker) ----> a consumer. 

- producer: in the folder `src/cli`, you can find the Python script: `producer_from_cli.py`. This script contains code that writes one record to a Kinesis Data Stream. You will call this script from a command line interface (CLI) and pass in two arguments: the name of the Kinesis Data Stream and a JSON string representing the message record.<br>

- router: you will create a Kinesis Data Stream that will act as a router between a producer and a consumer<br>

- consumer: in the same folder `src/cli`, you can find the Python script: `consumer_from_cli.py` which you will also call from the command line interface (CLI). It takes in one argument which is the name of the Kinesis Data Stream from which the consumer will read the message records.

<a id='1-2'></a>
### 1.2 - Shards and Iterators

- A __shard__ is a uniquely identified sequence of data records in a stream. Each stream consists of one or more shards, which determine the stream’s capacity.

- A __shard iterator__ is a token that tells Kinesis where to start reading data from within a shard. You use it to retrieve records using the GetRecords API. 
  It acts like a pointer that enables you to read data records from a specific position in a shard within a stream.

##### Types of Shard Iterators
When you request a shard iterator, you specify the type, which determines where in the shard the iterator starts:

- TRIM_HORIZON: Start from the oldest available record.
- LATEST: Start from the most recent record (new data only).
- AT_SEQUENCE_NUMBER: Start from a specific sequence number.
- AFTER_SEQUENCE_NUMBER: Start right after a specific sequence number.
- AT_TIMESTAMP: Start from records at or after a specific timestamp.

##### Example Usage

```python
response = kinesis_client.get_shard_iterator(
    StreamName='my-stream',
    ShardId='shardId-000000000000',
    ShardIteratorType='LATEST'
)
shard_iterator = response['ShardIterator']

```





## 2. CREATE A DATA STREAM
<a id='1-1'></a>
#### Get the link to the AWS console

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
## CONSUMING FROM THE STREAM

<a id='3-1'></a>
## Understanding consumer_from_cli.py

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
Class representing a pair of a shard ID and its corresponding shard iterator.

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
### b) poll_shards()
the poll_shards function continuously reads records from Kinesis shards:

- Decodes and logs each record.
- Updates shard iterators to maintain progress.
- Handles errors gracefully.
- Sleeps briefly between polling cycles.



<a id='3-2'></a>
### Running consumer_from_cli.py

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
## PRODUCE: WRITE TO THE STREAM

<a id='4-1'></a>
### Understanding producer_from_cli.py
The script sends a single JSON-formatted record to an Amazon Kinesis data stream using command-line arguments.

Workflow:
1. Parse command-line arguments.
2. Convert the JSON string to a Python dictionary.
3. Send the record to the specified Kinesis stream using put_record().
4. Use the session_id from the JSON as the partition key.
5. Log the result or any errors.

#### kinesis.put_record()
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
### Running producer_from_cli.py



```bash
cd src/cli/
python producer_from_cli.py --stream de-c2w2lab1-kinesis-data-stream-cli --json_string '{"session_id": "a1", "customer_number": 100, "city": "Washington", "country": "USA", "credit_limit": 1000, "browse_history": [ {"product_code": "Product1", "quantity": 2, "in_shopping_cart": true}, {"product_code": "Product2", "quantity": 1, "in_shopping_cart": false}]}'
```



## IMPLEMENTING A STREAMING ETL PROCESS

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

The subprocess module in Python is used to spawn new processes, connect to their input/output/error pipes, and obtain their return codes. It's a powerful tool for running shell commands or external programs from within a Python script.

``` python
import subprocess

subprocess.run(
    ['aws', 'sts', 'get-caller-identity', '--query', 'Account', '--output', 'text'],
    capture_output=True,
    text=True
).stdout.strip()

```

* aws sts get-caller-identity: Gets details about the IAM identity used to make the request.
* --query 'Account': Filters the output to show only the AWS account ID.
* --output text: Returns the result as plain text (not JSON).
* capture_output=True: Captures the command's output.
* text=True: Ensures the output is returned as a string (not bytes).
* .stdout.strip(): Removes any leading/trailing whitespace or newlines.
