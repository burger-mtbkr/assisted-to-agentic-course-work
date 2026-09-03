namespace ConfigApi.Service.Services.Applications;

public interface IApplicationService
{
    IReadOnlyList<Application> GetAll();

    Application? GetById(string id);

    Task<Application> CreateAsync(Application application);

    Task<Application?> UpdateAsync(string id, Application application);

    /// <summary>
    /// Returns null when the application does not exist, false when the
    /// delete was rejected because configurations still exist for it, and
    /// true when the application was deleted.
    /// </summary>
    Task<bool?> DeleteAsync(string id);
}
