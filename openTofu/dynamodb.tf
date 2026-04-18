# Aidez-vous du TP 4

resource "aws_dynamodb_table" "basic-dynamodb-table" {
  name           = "table-reseau-bpr"
  billing_mode   = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "user" #id_user 
  range_key      = "id"   #id_publi

  attribute {
    name = "user"
    type = "S"
  }

  attribute {
    name = "id"
    type = "S"
  }
}

# A décommenter quand la table est définie !!
output "dynamotablename" {
  description = "The postagram bucket name"
  value       = aws_dynamodb_table.basic-dynamodb-table.name
}