namespace ConfigApi.Service.Infrastructure.DynamoDb;

public class DynamoDbSettings
{
    public Dictionary<string, string> TableNames { get; set; } = new();

    public int ScanCacheSeconds { get; set; } = 300;
}
