using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.DocumentModel;

namespace ConfigApi.Service.Infrastructure.DynamoDb;

/// <summary>
/// Composite (partition key + sort key) table wrapper. Reuses the same
/// DynamoDbTableCache (scan-once, TTL-cached, invalidate-on-write) and the
/// same Document round-trip as DynamoDbCollection&lt;T&gt; — only the key-building
/// and GetItem/DeleteItem request shape differ (two-attribute key instead of one).
/// </summary>
public class DynamoDbCompositeKeyCollection<T> : IDynamoDbCompositeKeyCollection<T> where T : class
{
    private readonly ITable _table;
    private readonly string _tableName;
    private readonly DynamoDbTableCache _cache;
    private readonly TimeSpan _cacheTtl;
    private readonly string _partitionKeyName;
    private readonly Func<T, string> _partitionKeyAccessor;
    private readonly string _sortKeyName;
    private readonly Func<T, string> _sortKeyAccessor;

    public DynamoDbCompositeKeyCollection(
        IAmazonDynamoDB client,
        DynamoDbTableCache cache,
        string tableName,
        int scanCacheSeconds,
        string partitionKeyName,
        Func<T, string> partitionKeyAccessor,
        string sortKeyName,
        Func<T, string> sortKeyAccessor)
    {
        _cache = cache;
        _tableName = tableName;
        _cacheTtl = TimeSpan.FromSeconds(scanCacheSeconds);
        _partitionKeyName = partitionKeyName;
        _partitionKeyAccessor = partitionKeyAccessor;
        _sortKeyName = sortKeyName;
        _sortKeyAccessor = sortKeyAccessor;
        _table = new TableBuilder(client, tableName)
            .AddHashKey(partitionKeyName, DynamoDBEntryType.String)
            .AddRangeKey(sortKeyName, DynamoDBEntryType.String)
            .Build();
    }

    public IQueryable<T> AsQueryable()
    {
        return ScanAllAsync().GetAwaiter().GetResult().AsQueryable();
    }

    public T? GetByKey(string partitionKeyValue, string sortKeyValue)
    {
        return GetByKeyAsync(partitionKeyValue, sortKeyValue).GetAwaiter().GetResult();
    }

    public async Task<T?> GetByKeyAsync(string partitionKeyValue, string sortKeyValue, CancellationToken ct = default)
    {
        var document = await _table.GetItemAsync(BuildKey(partitionKeyValue, sortKeyValue), ct);
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
            var existing = await GetByKeyAsync(_partitionKeyAccessor(item), _sortKeyAccessor(item));
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

    public async Task<bool> DeleteOneAsync(string partitionKeyValue, string sortKeyValue)
    {
        var existing = await GetByKeyAsync(partitionKeyValue, sortKeyValue);
        if (existing is null)
        {
            return false;
        }

        await _table.DeleteItemAsync(BuildKey(partitionKeyValue, sortKeyValue));
        _cache.Invalidate(_tableName);
        return true;
    }

    private Document BuildKey(string partitionKeyValue, string sortKeyValue)
    {
        return new Document
        {
            [_partitionKeyName] = partitionKeyValue,
            [_sortKeyName] = sortKeyValue
        };
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
