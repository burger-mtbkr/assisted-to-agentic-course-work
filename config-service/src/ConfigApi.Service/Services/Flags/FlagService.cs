namespace ConfigApi.Service.Services.Flags;

public class FlagService : IFlagService
{
    private readonly IFlagRepository _flagRepository;
    private readonly IApplicationRepository _applicationRepository;

    public FlagService(
        IFlagRepository flagRepository,
        IApplicationRepository applicationRepository)
    {
        _flagRepository = flagRepository;
        _applicationRepository = applicationRepository;
    }

    public IReadOnlyList<Flag> GetAllForApplication(string applicationId) =>
        _flagRepository.GetAllForApplication(applicationId);

    public Flag? GetByKey(string applicationId, string flagKey) =>
        _flagRepository.GetByKey(applicationId, flagKey);

    public async Task<Flag> CreateAsync(string applicationId, Flag flag)
    {
        var application = _applicationRepository.GetById(applicationId);
        if (application is null)
        {
            throw new ApplicationNotFoundException($"Application '{applicationId}' was not found.");
        }

        if (!IsValidFlagKey(flag.FlagKey))
        {
            throw new ValidationException(
                "Flag key is invalid.",
                new Dictionary<string, string>
                {
                    ["flagKey"] = "Must contain only letters, digits, '.', '_' or '-'."
                });
        }

        var existing = _flagRepository.GetByKey(applicationId, flag.FlagKey);
        if (existing is not null)
        {
            throw new DuplicateFlagKeyException(
                $"Flag key '{flag.FlagKey}' already exists for application '{applicationId}'.");
        }

        flag.ApplicationId = applicationId;
        flag.CreatedDate = DateTime.UtcNow;

        return await _flagRepository.CreateAsync(flag);
    }

    public async Task<Flag?> UpdateAsync(string applicationId, string flagKey, Flag flag)
    {
        var existing = _flagRepository.GetByKey(applicationId, flagKey);
        if (existing is null)
        {
            return null;
        }

        existing.Enabled = flag.Enabled;
        existing.Description = flag.Description;

        await _flagRepository.UpdateAsync(existing);
        return existing;
    }

    public async Task<bool> DeleteAsync(string applicationId, string flagKey) =>
        await _flagRepository.DeleteAsync(applicationId, flagKey);

    private static bool IsValidFlagKey(string flagKey)
    {
        if (string.IsNullOrWhiteSpace(flagKey))
        {
            return false;
        }

        return flagKey.All(c => char.IsLetterOrDigit(c) || c is '.' or '_' or '-');
    }
}
