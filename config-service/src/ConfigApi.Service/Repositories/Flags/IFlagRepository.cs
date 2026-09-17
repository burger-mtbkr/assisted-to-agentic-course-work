namespace ConfigApi.Service.Repositories.Flags;

public interface IFlagRepository
{
    IReadOnlyList<Flag> GetAllForApplication(string applicationId);

    Flag? GetByKey(string applicationId, string flagKey);

    Task<Flag> CreateAsync(Flag flag);

    Task<bool> UpdateAsync(Flag flag);

    Task<bool> DeleteAsync(string applicationId, string flagKey);
}
