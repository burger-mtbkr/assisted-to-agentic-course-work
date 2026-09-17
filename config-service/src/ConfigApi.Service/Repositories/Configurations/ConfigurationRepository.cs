namespace ConfigApi.Service.Repositories.Configurations;

public class ConfigurationRepository : IConfigurationRepository
{
    private readonly IDynamoDbCompositeKeyCollection<Configuration> _collection;

    public ConfigurationRepository(IDynamoDbCompositeKeyCollection<Configuration> collection)
    {
        _collection = collection;
    }

    public IReadOnlyList<Configuration> GetAllForApplication(string applicationId) =>
        _collection.AsQueryable().Where(c => c.ApplicationId == applicationId).ToList();

    public Configuration? GetByKey(string applicationId, string configKey) =>
        _collection.GetByKey(applicationId, configKey);

    public async Task<Configuration> CreateAsync(Configuration configuration)
    {
        await _collection.InsertOneAsync(configuration);
        return configuration;
    }

    public async Task<bool> UpdateAsync(Configuration configuration) =>
        await _collection.ReplaceOneAsync(configuration);

    public async Task<bool> DeleteAsync(string applicationId, string configKey) =>
        await _collection.DeleteOneAsync(applicationId, configKey);
}
