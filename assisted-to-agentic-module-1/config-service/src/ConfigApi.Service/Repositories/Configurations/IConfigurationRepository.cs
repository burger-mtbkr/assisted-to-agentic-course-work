namespace ConfigApi.Service.Repositories.Configurations;

public interface IConfigurationRepository
{
    IReadOnlyList<Configuration> GetAllForApplication(string applicationId);

    Configuration? GetByKey(string applicationId, string configKey);

    Task<Configuration> CreateAsync(Configuration configuration);

    Task<bool> UpdateAsync(Configuration configuration);

    Task<bool> DeleteAsync(string applicationId, string configKey);
}
