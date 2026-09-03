namespace ConfigApi.Service.Services.Configurations;

public class ConfigurationService : IConfigurationService
{
    private readonly IConfigurationRepository _configurationRepository;
    private readonly IApplicationRepository _applicationRepository;

    public ConfigurationService(
        IConfigurationRepository configurationRepository,
        IApplicationRepository applicationRepository)
    {
        _configurationRepository = configurationRepository;
        _applicationRepository = applicationRepository;
    }

    public IReadOnlyList<Configuration> GetAllForApplication(string applicationId) =>
        _configurationRepository.GetAllForApplication(applicationId);

    public Configuration? GetByKey(string applicationId, string configKey) =>
        _configurationRepository.GetByKey(applicationId, configKey);

    public async Task<Configuration> CreateAsync(string applicationId, Configuration configuration)
    {
        var application = _applicationRepository.GetById(applicationId);
        if (application is null)
        {
            throw new ApplicationNotFoundException($"Application '{applicationId}' was not found.");
        }

        if (!IsValidConfigKey(configuration.ConfigKey))
        {
            throw new ValidationException(
                "Configuration key is invalid.",
                new Dictionary<string, string>
                {
                    ["configKey"] = "Must contain only letters, digits, '.', '_' or '-'."
                });
        }

        var existing = _configurationRepository.GetByKey(applicationId, configuration.ConfigKey);
        if (existing is not null)
        {
            throw new DuplicateConfigurationKeyException(
                $"Configuration key '{configuration.ConfigKey}' already exists for application '{applicationId}'.");
        }

        configuration.ApplicationId = applicationId;
        configuration.CreatedDate = DateTime.UtcNow;

        return await _configurationRepository.CreateAsync(configuration);
    }

    public async Task<Configuration?> UpdateAsync(string applicationId, string configKey, Configuration configuration)
    {
        var existing = _configurationRepository.GetByKey(applicationId, configKey);
        if (existing is null)
        {
            return null;
        }

        existing.Value = configuration.Value;
        existing.Description = configuration.Description;

        await _configurationRepository.UpdateAsync(existing);
        return existing;
    }

    public async Task<bool> DeleteAsync(string applicationId, string configKey) =>
        await _configurationRepository.DeleteAsync(applicationId, configKey);

    private static bool IsValidConfigKey(string configKey)
    {
        if (string.IsNullOrWhiteSpace(configKey))
        {
            return false;
        }

        return configKey.All(c => char.IsLetterOrDigit(c) || c is '.' or '_' or '-');
    }
}
