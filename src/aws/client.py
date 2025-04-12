import boto3
from typing import Optional

from src.aws.config import get_aws_settings

class AWSClient:
    def __init__(self):
        self.settings = get_aws_settings()
        self.session = boto3.Session(
            aws_access_key_id=self.settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self.settings.AWS_SECRET_ACCESS_KEY,
            region_name=self.settings.AWS_REGION
        )
        
    def get_s3_client(self):
        return self.session.client('s3')
        
    def get_sqs_client(self):
        return self.session.client('sqs')
        
    def get_sns_client(self):
        return self.session.client('sns')
        
    def get_dynamodb_client(self):
        return self.session.client('dynamodb')
        
    def get_lambda_client(self):
        return self.session.client('lambda') 