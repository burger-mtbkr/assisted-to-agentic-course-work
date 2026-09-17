using Amazon.DynamoDBv2;

namespace ConfigApi.Provisioning.Migrations;

public interface ITableMigration
{
    int Version { get; }

    string Description { get; }

    Task ApplyAsync(IAmazonDynamoDB client);
}
