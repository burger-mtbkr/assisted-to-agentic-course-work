using System.Text.Json;
using Amazon.DynamoDBv2.DocumentModel;

namespace ConfigApi.Service.Infrastructure.DynamoDb;

/// <summary>
/// Round-trips domain entities through DynamoDB's Document model via JSON,
/// so repositories never have to build AttributeValue maps by hand.
/// </summary>
public static class DynamoDbJsonSerializer
{
    private static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web);

    public static Document ToDocument<T>(T item) where T : class
    {
        var json = JsonSerializer.Serialize(item, Options);
        return Document.FromJson(json);
    }

    public static T FromDocument<T>(Document document) where T : class
    {
        var json = document.ToJson();
        return JsonSerializer.Deserialize<T>(json, Options)
            ?? throw new InvalidOperationException($"Failed to deserialize DynamoDB document into {typeof(T).Name}.");
    }
}
