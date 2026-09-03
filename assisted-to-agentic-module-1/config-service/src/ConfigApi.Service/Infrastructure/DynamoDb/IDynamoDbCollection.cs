namespace ConfigApi.Service.Infrastructure.DynamoDb;

/// <summary>
/// Single partition-key ("id") table abstraction, ported from income-service's
/// IDynamoDbCollection&lt;T&gt;.
/// </summary>
public interface IDynamoDbCollection<T> where T : class
{
    IQueryable<T> AsQueryable();

    T? GetById(string id);

    Task<T?> GetByIdAsync(string id, CancellationToken ct = default);

    Task InsertOneAsync(T item);

    Task<bool> ReplaceOneAsync(T item, bool upsert = false);

    Task<bool> DeleteOneAsync(string? id);
}
