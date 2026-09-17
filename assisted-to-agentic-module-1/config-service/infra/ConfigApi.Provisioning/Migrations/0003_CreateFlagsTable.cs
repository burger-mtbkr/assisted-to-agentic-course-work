using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.Model;

namespace ConfigApi.Provisioning.Migrations;

public class CreateFlagsTable : ITableMigration
{
    public int Version => 3;

    public string Description => "Create the flags table (PK: applicationId, SK: flagKey).";

    public async Task ApplyAsync(IAmazonDynamoDB client)
    {
        const string tableName = "flags";

        try
        {
            await client.DescribeTableAsync(tableName);
            Console.WriteLine($"[{Version:0000}] {tableName} already exists, skipping.");
        }
        catch (ResourceNotFoundException)
        {
            Console.WriteLine($"[{Version:0000}] Creating table {tableName}...");

            await client.CreateTableAsync(new CreateTableRequest
            {
                TableName = tableName,
                BillingMode = BillingMode.PAY_PER_REQUEST,
                AttributeDefinitions =
                [
                    new AttributeDefinition("applicationId", ScalarAttributeType.S),
                    new AttributeDefinition("flagKey", ScalarAttributeType.S)
                ],
                KeySchema =
                [
                    new KeySchemaElement("applicationId", KeyType.HASH),
                    new KeySchemaElement("flagKey", KeyType.RANGE)
                ]
            });

            Console.WriteLine($"[{Version:0000}] {tableName} created.");
        }
    }
}
