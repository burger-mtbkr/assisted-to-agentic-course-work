using Amazon;
using Amazon.DynamoDBv2;
using ConfigApi.Service.Infrastructure.DynamoDb;
using ConfigApi.Service.Models.Applications;
using ConfigApi.Service.Models.Configurations;
using ConfigApi.Service.Models.Flags;
using Microsoft.Extensions.Options;

namespace ConfigApi.Service.Ignition;

public static class DynamoDbIgnition
{
    public static void ConfigureDynamoDb(this WebApplicationBuilder builder)
    {
        builder.Services.Configure<DynamoDbSettings>(builder.Configuration.GetSection("DynamoDB"));
        builder.Services.AddMemoryCache();
        builder.Services.AddScoped<DynamoDbTableCache>();

        var region = builder.Configuration["AWS_REGION"] ?? "ap-southeast-6";
        builder.Services.AddSingleton<IAmazonDynamoDB>(_ =>
            new AmazonDynamoDBClient(RegionEndpoint.GetBySystemName(region)));

        RegisterCollection<Application>(builder, "applications", a => a.Id);

        RegisterCompositeKeyCollection<Configuration>(
            builder,
            "configurations",
            "applicationId",
            c => c.ApplicationId,
            "configKey",
            c => c.ConfigKey);

        RegisterCompositeKeyCollection<Flag>(
            builder,
            "flags",
            "applicationId",
            f => f.ApplicationId,
            "flagKey",
            f => f.FlagKey);
    }

    private static void RegisterCollection<T>(
        WebApplicationBuilder builder,
        string tableKey,
        Func<T, string> idAccessor) where T : class
    {
        builder.Services.AddScoped<IDynamoDbCollection<T>>(sp =>
        {
            var settings = sp.GetRequiredService<IOptions<DynamoDbSettings>>().Value;
            var client = sp.GetRequiredService<IAmazonDynamoDB>();
            var cache = sp.GetRequiredService<DynamoDbTableCache>();
            var tableName = settings.TableNames[tableKey];
            return new DynamoDbCollection<T>(client, cache, tableName, settings.ScanCacheSeconds, idAccessor);
        });
    }

    private static void RegisterCompositeKeyCollection<T>(
        WebApplicationBuilder builder,
        string tableKey,
        string partitionKeyName,
        Func<T, string> partitionKeyAccessor,
        string sortKeyName,
        Func<T, string> sortKeyAccessor) where T : class
    {
        builder.Services.AddScoped<IDynamoDbCompositeKeyCollection<T>>(sp =>
        {
            var settings = sp.GetRequiredService<IOptions<DynamoDbSettings>>().Value;
            var client = sp.GetRequiredService<IAmazonDynamoDB>();
            var cache = sp.GetRequiredService<DynamoDbTableCache>();
            var tableName = settings.TableNames[tableKey];
            return new DynamoDbCompositeKeyCollection<T>(
                client,
                cache,
                tableName,
                settings.ScanCacheSeconds,
                partitionKeyName,
                partitionKeyAccessor,
                sortKeyName,
                sortKeyAccessor);
        });
    }
}
