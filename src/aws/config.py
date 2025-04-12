from pydantic_settings import BaseSettings
from functools import lru_cache

class AWSSettings(BaseSettings):
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"
    
    # S3 settings
    S3_BUCKET_NAME: str
    
    # SQS settings
    SQS_QUEUE_URL: str
    
    # SNS settings
    SNS_TOPIC_ARN: str
    
    # DynamoDB settings
    DYNAMODB_TABLE_NAME: str
    
    # Lambda settings
    LAMBDA_FUNCTION_NAME: str
    
    class Config:
        env_prefix = "AWS_"
        env_file = ".env"

@lru_cache()
def get_aws_settings():
    return AWSSettings() 