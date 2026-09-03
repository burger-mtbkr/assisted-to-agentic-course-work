namespace ConfigApi.Service.Repositories.Applications;

public interface IApplicationRepository
{
    IReadOnlyList<Application> GetAll();

    Application? GetById(string id);

    Application? GetByName(string name);

    Task<Application> CreateAsync(Application application);

    Task<bool> UpdateAsync(Application application);

    Task<bool> DeleteAsync(string id);
}
