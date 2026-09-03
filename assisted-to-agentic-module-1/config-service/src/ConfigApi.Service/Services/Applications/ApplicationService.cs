namespace ConfigApi.Service.Services.Applications;

public class ApplicationService : IApplicationService
{
    private readonly IApplicationRepository _applicationRepository;
    private readonly IConfigurationRepository _configurationRepository;

    public ApplicationService(
        IApplicationRepository applicationRepository,
        IConfigurationRepository configurationRepository)
    {
        _applicationRepository = applicationRepository;
        _configurationRepository = configurationRepository;
    }

    public IReadOnlyList<Application> GetAll() => _applicationRepository.GetAll();

    public Application? GetById(string id) => _applicationRepository.GetById(id);

    public async Task<Application> CreateAsync(Application application)
    {
        var existingByName = _applicationRepository.GetByName(application.Name);
        if (existingByName is not null)
        {
            throw new DuplicateApplicationNameException(
                $"An application named '{application.Name}' already exists.");
        }

        application.Id = string.IsNullOrWhiteSpace(application.Id) ? Guid.NewGuid().ToString() : application.Id;
        application.CreatedDate = DateTime.UtcNow;

        return await _applicationRepository.CreateAsync(application);
    }

    public async Task<Application?> UpdateAsync(string id, Application application)
    {
        var existing = _applicationRepository.GetById(id);
        if (existing is null)
        {
            return null;
        }

        existing.Name = application.Name;
        existing.Description = application.Description;

        await _applicationRepository.UpdateAsync(existing);
        return existing;
    }

    public async Task<bool?> DeleteAsync(string id)
    {
        var existing = _applicationRepository.GetById(id);
        if (existing is null)
        {
            return null;
        }

        var hasConfigurations = _configurationRepository.GetAllForApplication(id).Any();
        if (hasConfigurations)
        {
            return false;
        }

        return await _applicationRepository.DeleteAsync(id);
    }
}
