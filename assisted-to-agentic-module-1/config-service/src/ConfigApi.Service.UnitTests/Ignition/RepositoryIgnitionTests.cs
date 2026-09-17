using ConfigApi.Service.Ignition;
using Microsoft.Extensions.DependencyInjection;

namespace ConfigApi.Service.UnitTests.Ignition;

public class RepositoryIgnitionTests
{
    [Fact]
    public void ConfigureRepositories_RegistersApplicationRepository_AsScoped()
    {
        var services = new ServiceCollection();

        services.ConfigureRepositories();

        var descriptor = Assert.Single(services, d => d.ServiceType == typeof(IApplicationRepository));
        Assert.Equal(typeof(ApplicationRepository), descriptor.ImplementationType);
        Assert.Equal(ServiceLifetime.Scoped, descriptor.Lifetime);
    }

    [Fact]
    public void ConfigureRepositories_RegistersConfigurationRepository_AsScoped()
    {
        var services = new ServiceCollection();

        services.ConfigureRepositories();

        var descriptor = Assert.Single(services, d => d.ServiceType == typeof(IConfigurationRepository));
        Assert.Equal(typeof(ConfigurationRepository), descriptor.ImplementationType);
        Assert.Equal(ServiceLifetime.Scoped, descriptor.Lifetime);
    }

    [Fact]
    public void ConfigureRepositories_RegistersFlagRepository_AsScoped()
    {
        var services = new ServiceCollection();

        services.ConfigureRepositories();

        var descriptor = Assert.Single(services, d => d.ServiceType == typeof(IFlagRepository));
        Assert.Equal(typeof(FlagRepository), descriptor.ImplementationType);
        Assert.Equal(ServiceLifetime.Scoped, descriptor.Lifetime);
    }
}
