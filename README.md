
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
- [ 2 - Create a Data Stream](#2)
- [ 3 - UNDERSTANDING consumer_from_cli.py](#3)
  - [ a) Parse Stream Name with argparse](#3-a)
  - [ b) fetch_shards_and_iterators()](#3-b)
  - [ c) poll_shards()]
- [ 4 - RUNNING consumer_from_cli.py](#4)
- [ 2 - Implementing a Streaming ETL Process](#2)
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
## UNDERSTANDING consumer_from_cli.py

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


<a id='3-b'></a>
### b) poll_shards()
the poll_shards function continuously reads records from Kinesis shards:

- Decodes and logs each record.
- Updates shard iterators to maintain progress.
- Handles errors gracefully.
- Sleeps briefly between polling cycles.


<a id='4'></a>
### RUNNING consumer_from_cli.py

#### First run of the script
This consumer script iterates through all the shards of the data stream, reading all the records from each shard and printing some information about each record in the terminal. 

The consumer script expects one argument (the name of the data stream) which is specified using the --stream flag followed by the data stream name. 
To execute this python script run

```bash
cd src/cli/
python consumer_from_cli.py --stream de-c2w2lab1-kinesis-data-stream-cli
```

In this first run nothing will now appear even after waiting for 1 or 2 minutes. This is because the script is consuming from a data stream that is currently empty.

















The subprocess module in Python is used to spawn new processes, connect to their input/output/error pipes, and obtain their return codes. It's a powerful tool for running shell commands or external programs from within a Python script.

``` python
import subprocess

subprocess.run(
    ['aws', 'sts', 'get-caller-identity', '--query', 'Account', '--output', 'text'],
    capture_output=True,
    text=True
).stdout.strip()

```

aws sts get-caller-identity: Gets details about the IAM identity used to make the request.
--query 'Account': Filters the output to show only the AWS account ID.
--output text: Returns the result as plain text (not JSON).
capture_output=True: Captures the command's output.
text=True: Ensures the output is returned as a string (not bytes).
.stdout.strip(): Removes any leading/trailing whitespace or newlines.
