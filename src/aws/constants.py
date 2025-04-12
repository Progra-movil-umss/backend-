# Error messages
AWS_CREDENTIALS_ERROR = "Error al autenticar con AWS"
S3_UPLOAD_ERROR = "Error al subir archivo a S3"
SQS_SEND_ERROR = "Error al enviar mensaje a SQS"
SNS_PUBLISH_ERROR = "Error al publicar mensaje en SNS"
DYNAMODB_ERROR = "Error al operar con DynamoDB"
LAMBDA_ERROR = "Error al invocar función Lambda"

# Success messages
S3_UPLOAD_SUCCESS = "Archivo subido exitosamente a S3"
SQS_SEND_SUCCESS = "Mensaje enviado exitosamente a SQS"
SNS_PUBLISH_SUCCESS = "Mensaje publicado exitosamente en SNS"
DYNAMODB_SUCCESS = "Operación completada exitosamente en DynamoDB"
LAMBDA_SUCCESS = "Función Lambda invocada exitosamente"

# Validation messages
INVALID_BUCKET_NAME = "Nombre de bucket S3 inválido"
INVALID_QUEUE_URL = "URL de cola SQS inválida"
INVALID_TOPIC_ARN = "ARN de tema SNS inválido"
INVALID_TABLE_NAME = "Nombre de tabla DynamoDB inválido"
INVALID_FUNCTION_NAME = "Nombre de función Lambda inválido" 