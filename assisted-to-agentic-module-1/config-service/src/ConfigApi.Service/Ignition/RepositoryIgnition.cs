using ConfigApi.Service.Repositories.Applications;
using ConfigApi.Service.Repositories.Configurations;

namespace ConfigApi.Service.Ignition;

public static class RepositoryIgnition
{
    public static void ConfigureRepositories(this IServiceCollection services)
    {
        services.AddScoped<IApplicationRepository, ApplicationRepository>();
        services.AddScoped<IConfigurationRepository, ConfigurationRepository>();
    }
}
