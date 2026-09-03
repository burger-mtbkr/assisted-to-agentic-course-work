using Amazon.DynamoDBv2.DocumentModel;
using Microsoft.Extensions.Caching.Memory;

namespace ConfigApi.Service.Infrastructure.DynamoDb;

/// <summary>
/// Scan-once, TTL-cached, invalidate-on-write cache of a table's full item set.
/// Registered scoped so a single request reuses one scan; the underlying
/// IMemoryCache store is shared across requests for the TTL window.
/// </summary>
public class DynamoDbTableCache
{
    private readonly IMemoryCache _cache;

    public DynamoDbTableCache(IMemoryCache cache)
    {
        _cache = cache;
    }

    public async Task<List<Document>> GetOrAddAsync(
        string tableName,
        Func<Task<List<Document>>> factory,
        TimeSpan ttl)
    {
        if (_cache.TryGetValue(CacheKey(tableName), out List<Document>? cached) && cached is not null)
        {
            return cached;
        }

        var items = await factory();
        _cache.Set(CacheKey(tableName), items, ttl);
        return items;
    }

    public void Invalidate(string tableName)
    {
        _cache.Remove(CacheKey(tableName));
    }

    private static string CacheKey(string tableName) => $"dynamodb:table:{tableName}";
}
