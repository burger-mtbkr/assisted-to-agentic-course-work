using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.Model;

namespace ConfigApi.Provisioning.Migrations;

public class CreateApplicationsTable : ITableMigration
{
    public int Version => 1;

    public string Description => "Create the applications table (PK: id).";

    public async Task ApplyAsync(IAmazonDynamoDB client)
    {
        const string tableName = "applications";

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
                    new AttributeDefinition("id", ScalarAttributeType.S)
                ],
                KeySchema =
                [
                    new KeySchemaElement("id", KeyType.HASH)
                ]
            });

            Console.WriteLine($"[{Version:0000}] {tableName} created.");
        }
    }
}
