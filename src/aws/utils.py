import re
from typing import Optional

from src.aws import constants

def validate_bucket_name(bucket_name: str) -> Optional[str]:
    bucket_regex = r'^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$'
    if not re.match(bucket_regex, bucket_name):
        return constants.INVALID_BUCKET_NAME
    return None

def validate_queue_url(queue_url: str) -> Optional[str]:
    queue_url_regex = r'^https://sqs\.[a-z0-9-]+\.amazonaws\.com/\d+/[a-zA-Z0-9_-]+$'
    if not re.match(queue_url_regex, queue_url):
        return constants.INVALID_QUEUE_URL
    return None

def validate_topic_arn(topic_arn: str) -> Optional[str]:
    topic_arn_regex = r'^arn:aws:sns:[a-z0-9-]+:\d+:[a-zA-Z0-9_-]+$'
    if not re.match(topic_arn_regex, topic_arn):
        return constants.INVALID_TOPIC_ARN
    return None

def validate_table_name(table_name: str) -> Optional[str]:
    table_name_regex = r'^[a-zA-Z0-9_.-]{3,255}$'
    if not re.match(table_name_regex, table_name):
        return constants.INVALID_TABLE_NAME
    return None

def validate_function_name(function_name: str) -> Optional[str]:
    function_name_regex = r'^[a-zA-Z0-9-_]{1,64}$'
    if not re.match(function_name_regex, function_name):
        return constants.INVALID_FUNCTION_NAME
    return None 