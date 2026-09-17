namespace ConfigApi.Service.Services.Flags;

public interface IFlagService
{
    IReadOnlyList<Flag> GetAllForApplication(string applicationId);

    Flag? GetByKey(string applicationId, string flagKey);

    Task<Flag> CreateAsync(string applicationId, Flag flag);

    Task<Flag?> UpdateAsync(string applicationId, string flagKey, Flag flag);

    Task<bool> DeleteAsync(string applicationId, string flagKey);
}
