using Amazon;
using Amazon.DynamoDBv2;
using ConfigApi.Provisioning.Migrations;

DotNetEnv.Env.Load();

var region = Environment.GetEnvironmentVariable("AWS_REGION") ?? "ap-southeast-6";
using var client = new AmazonDynamoDBClient(RegionEndpoint.GetBySystemName(region));

ITableMigration[] migrations =
[
    new CreateApplicationsTable(),
    new CreateConfigurationsTable(),
    new CreateFlagsTable()
];

foreach (var migration in migrations.OrderBy(m => m.Version))
{
    Console.WriteLine($"Running migration {migration.Version:0000}: {migration.Description}");
    await migration.ApplyAsync(client);
}

Console.WriteLine("Provisioning complete.");
