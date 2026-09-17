using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.DocumentModel;

namespace ConfigApi.Service.Infrastructure.DynamoDb;

/// <summary>
/// Single partition-key ("id") table wrapper, ported from income-service's
/// DynamoDbCollection&lt;T&gt;. Scans are TTL-cached via DynamoDbTableCache and
/// invalidated on every write; point reads go straight to GetItem.
/// </summary>
public class DynamoDbCollection<T> : IDynamoDbCollection<T> where T : class
{
    private readonly ITable _table;
    private readonly string _tableName;
    private readonly DynamoDbTableCache _cache;
    private readonly TimeSpan _cacheTtl;
    private readonly Func<T, string> _idAccessor;

    public DynamoDbCollection(
        IAmazonDynamoDB client,
        DynamoDbTableCache cache,
        string tableName,
        int scanCacheSeconds,
        Func<T, string> idAccessor)
    {
        _cache = cache;
        _tableName = tableName;
        _cacheTtl = TimeSpan.FromSeconds(scanCacheSeconds);
        _idAccessor = idAccessor;
        _table = new TableBuilder(client, tableName)
            .AddHashKey("id", DynamoDBEntryType.String)
            .Build();
    }

    public IQueryable<T> AsQueryable()
    {
        return ScanAllAsync().GetAwaiter().GetResult().AsQueryable();
    }

    public T? GetById(string id)
    {
        return GetByIdAsync(id).GetAwaiter().GetResult();
    }

    public async Task<T?> GetByIdAsync(string id, CancellationToken ct = default)
    {
        var document = await _table.GetItemAsync(id, ct);
        return document is null ? null : DynamoDbJsonSerializer.FromDocument<T>(document);
    }

    public async Task InsertOneAsync(T item)
    {
        var document = DynamoDbJsonSerializer.ToDocument(item);
        await _table.PutItemAsync(document);
        _cache.Invalidate(_tableName);
    }

    public async Task<bool> ReplaceOneAsync(T item, bool upsert = false)
    {
        if (!upsert)
        {
            var existing = await GetByIdAsync(_idAccessor(item));
            if (existing is null)
            {
                return false;
            }
        }

        var document = DynamoDbJsonSerializer.ToDocument(item);
        await _table.PutItemAsync(document);
        _cache.Invalidate(_tableName);
        return true;
    }

    public async Task<bool> DeleteOneAsync(string? id)
    {
        if (string.IsNullOrEmpty(id))
        {
            return false;
        }

        var existing = await GetByIdAsync(id);
        if (existing is null)
        {
            return false;
        }

        await _table.DeleteItemAsync(id);
        _cache.Invalidate(_tableName);
        return true;
    }

    private async Task<List<T>> ScanAllAsync()
    {
        var documents = await _cache.GetOrAddAsync(_tableName, async () =>
        {
            var search = _table.Scan(new ScanOperationConfig());
            var results = new List<Document>();
            do
            {
                var batch = await search.GetNextSetAsync();
                results.AddRange(batch);
            } while (!search.IsDone);

            return results;
        }, _cacheTtl);

        return documents.Select(DynamoDbJsonSerializer.FromDocument<T>).ToList();
    }
}
