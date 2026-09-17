namespace ConfigApi.Service.Repositories.Applications;

public class ApplicationRepository : IApplicationRepository
{
    private readonly IDynamoDbCollection<Application> _collection;

    public ApplicationRepository(IDynamoDbCollection<Application> collection)
    {
        _collection = collection;
    }

    public IReadOnlyList<Application> GetAll() => _collection.AsQueryable().ToList();

    public Application? GetById(string id) => _collection.GetById(id);

    public Application? GetByName(string name) =>
        _collection.AsQueryable().FirstOrDefault(a => a.Name == name);

    public async Task<Application> CreateAsync(Application application)
    {
        await _collection.InsertOneAsync(application);
        return application;
    }

    public async Task<bool> UpdateAsync(Application application) =>
        await _collection.ReplaceOneAsync(application);

    public async Task<bool> DeleteAsync(string id) =>
        await _collection.DeleteOneAsync(id);
}
