using ConfigApi.Service.Repositories.Applications;
using ConfigApi.Service.Repositories.Configurations;
using ConfigApi.Service.Repositories.Flags;

namespace ConfigApi.Service.Ignition;

public static class RepositoryIgnition
{
    public static void ConfigureRepositories(this IServiceCollection services)
    {
        services.AddScoped<IApplicationRepository, ApplicationRepository>();
        services.AddScoped<IConfigurationRepository, ConfigurationRepository>();
        services.AddScoped<IFlagRepository, FlagRepository>();
    }
}
