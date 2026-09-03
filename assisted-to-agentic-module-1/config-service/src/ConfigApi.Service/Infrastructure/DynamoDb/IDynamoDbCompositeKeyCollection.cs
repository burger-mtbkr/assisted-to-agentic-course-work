namespace ConfigApi.Service.Infrastructure.DynamoDb;

/// <summary>
/// Composite (partition key + sort key) table abstraction. Required because
/// income-service's IDynamoDbCollection&lt;T&gt; is hard-wired to a single "id"
/// partition key and cannot express the configurations table's
/// (applicationId, configKey) key schema.
/// </summary>
public interface IDynamoDbCompositeKeyCollection<T> where T : class
{
    IQueryable<T> AsQueryable();

    T? GetByKey(string partitionKeyValue, string sortKeyValue);

    Task<T?> GetByKeyAsync(string partitionKeyValue, string sortKeyValue, CancellationToken ct = default);

    Task InsertOneAsync(T item);

    Task<bool> ReplaceOneAsync(T item, bool upsert = false);

    Task<bool> DeleteOneAsync(string partitionKeyValue, string sortKeyValue);
}
