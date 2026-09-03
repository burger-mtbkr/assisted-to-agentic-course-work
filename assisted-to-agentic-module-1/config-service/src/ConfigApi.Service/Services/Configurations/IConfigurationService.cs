namespace ConfigApi.Service.Services.Configurations;

public interface IConfigurationService
{
    IReadOnlyList<Configuration> GetAllForApplication(string applicationId);

    Configuration? GetByKey(string applicationId, string configKey);

    Task<Configuration> CreateAsync(string applicationId, Configuration configuration);

    Task<Configuration?> UpdateAsync(string applicationId, string configKey, Configuration configuration);

    Task<bool> DeleteAsync(string applicationId, string configKey);
}
