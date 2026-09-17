namespace ConfigApi.Service.Repositories.Flags;

public class FlagRepository : IFlagRepository
{
    private readonly IDynamoDbCompositeKeyCollection<Flag> _collection;

    public FlagRepository(IDynamoDbCompositeKeyCollection<Flag> collection)
    {
        _collection = collection;
    }

    public IReadOnlyList<Flag> GetAllForApplication(string applicationId) =>
        _collection.AsQueryable().Where(f => f.ApplicationId == applicationId).ToList();

    public Flag? GetByKey(string applicationId, string flagKey) =>
        _collection.GetByKey(applicationId, flagKey);

    public async Task<Flag> CreateAsync(Flag flag)
    {
        await _collection.InsertOneAsync(flag);
        return flag;
    }

    public async Task<bool> UpdateAsync(Flag flag) =>
        await _collection.ReplaceOneAsync(flag);

    public async Task<bool> DeleteAsync(string applicationId, string flagKey) =>
        await _collection.DeleteOneAsync(applicationId, flagKey);
}
