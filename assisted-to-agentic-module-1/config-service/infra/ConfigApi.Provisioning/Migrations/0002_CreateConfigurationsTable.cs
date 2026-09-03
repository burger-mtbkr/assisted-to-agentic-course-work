using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.Model;

namespace ConfigApi.Provisioning.Migrations;

public class CreateConfigurationsTable : ITableMigration
{
    public int Version => 2;

    public string Description => "Create the configurations table (PK: applicationId, SK: configKey).";

    public async Task ApplyAsync(IAmazonDynamoDB client)
    {
        const string tableName = "configurations";

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
                    new AttributeDefinition("configKey", ScalarAttributeType.S)
                ],
                KeySchema =
                [
                    new KeySchemaElement("applicationId", KeyType.HASH),
                    new KeySchemaElement("configKey", KeyType.RANGE)
                ]
            });

            Console.WriteLine($"[{Version:0000}] {tableName} created.");
        }
    }
}
