from pydantic import BaseModel
from typing import Optional, Dict, Any

class S3UploadResponse(BaseModel):
    bucket: str
    key: str
    url: str

class SQSMessage(BaseModel):
    message_id: str
    body: Dict[str, Any]
    attributes: Optional[Dict[str, Any]] = None

class SNSMessage(BaseModel):
    topic_arn: str
    message: str
    subject: Optional[str] = None
    message_attributes: Optional[Dict[str, Any]] = None

class DynamoDBItem(BaseModel):
    table_name: str
    item: Dict[str, Any]

class LambdaInvocationResponse(BaseModel):
    status_code: int
    payload: Dict[str, Any]
    execution_arn: Optional[str] = None 