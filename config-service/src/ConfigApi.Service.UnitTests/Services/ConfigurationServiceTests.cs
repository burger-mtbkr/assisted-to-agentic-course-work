using Moq;

namespace ConfigApi.Service.UnitTests.Services;

public class ConfigurationServiceTests
{
    private readonly Mock<IConfigurationRepository> _configurationRepository = new();
    private readonly Mock<IApplicationRepository> _applicationRepository = new();
    private readonly ConfigurationService _service;

    public ConfigurationServiceTests()
    {
        _service = new ConfigurationService(_configurationRepository.Object, _applicationRepository.Object);
    }

    [Fact]
    public async Task CreateAsync_Throws_ApplicationNotFoundException_WhenParentApplicationMissing()
    {
        _applicationRepository.Setup(r => r.GetById("app-1")).Returns((Application?)null);

        var configuration = new Configuration { ConfigKey = "key-a", Value = "value" };

        await Assert.ThrowsAsync<ApplicationNotFoundException>(
            () => _service.CreateAsync("app-1", configuration));
    }

    [Fact]
    public async Task CreateAsync_Throws_DuplicateConfigurationKeyException_OnSecondCreateWithSameKey()
    {
        var application = new Application { Id = "app-1", Name = "App" };
        _applicationRepository.Setup(r => r.GetById("app-1")).Returns(application);
        _configurationRepository
            .Setup(r => r.GetByKey("app-1", "key-a"))
            .Returns(new Configuration { ApplicationId = "app-1", ConfigKey = "key-a" });

        var configuration = new Configuration { ConfigKey = "key-a", Value = "value" };

        await Assert.ThrowsAsync<DuplicateConfigurationKeyException>(
            () => _service.CreateAsync("app-1", configuration));
    }

    [Fact]
    public async Task CreateAsync_Throws_ValidationException_WhenConfigKeyIsInvalid()
    {
        var application = new Application { Id = "app-1", Name = "App" };
        _applicationRepository.Setup(r => r.GetById("app-1")).Returns(application);

        var configuration = new Configuration { ConfigKey = "invalid/key", Value = "value" };

        await Assert.ThrowsAsync<ValidationException>(
            () => _service.CreateAsync("app-1", configuration));
    }

    [Fact]
    public async Task CreateAsync_PropagatesValidCreate()
    {
        var application = new Application { Id = "app-1", Name = "App" };
        _applicationRepository.Setup(r => r.GetById("app-1")).Returns(application);
        _configurationRepository.Setup(r => r.GetByKey("app-1", "key-a")).Returns((Configuration?)null);
        _configurationRepository
            .Setup(r => r.CreateAsync(It.IsAny<Configuration>()))
            .ReturnsAsync((Configuration c) => c);

        var configuration = new Configuration { ConfigKey = "key-a", Value = "value" };

        var result = await _service.CreateAsync("app-1", configuration);

        Assert.Equal("app-1", result.ApplicationId);
        Assert.Equal("key-a", result.ConfigKey);
        _configurationRepository.Verify(r => r.CreateAsync(It.IsAny<Configuration>()), Times.Once);
    }

    [Fact]
    public async Task UpdateAsync_ReturnsNull_WhenConfigurationDoesNotExist()
    {
        _configurationRepository.Setup(r => r.GetByKey("app-1", "key-a")).Returns((Configuration?)null);

        var result = await _service.UpdateAsync("app-1", "key-a", new Configuration { Value = "new-value" });

        Assert.Null(result);
    }

    [Fact]
    public async Task UpdateAsync_UpdatesValueAndDescription_WhenConfigurationExists()
    {
        var existing = new Configuration { ApplicationId = "app-1", ConfigKey = "key-a", Value = "old", Description = "old-desc" };
        _configurationRepository.Setup(r => r.GetByKey("app-1", "key-a")).Returns(existing);
        _configurationRepository.Setup(r => r.UpdateAsync(It.IsAny<Configuration>())).ReturnsAsync(true);

        var result = await _service.UpdateAsync("app-1", "key-a", new Configuration { Value = "new", Description = "new-desc" });

        Assert.NotNull(result);
        Assert.Equal("new", result!.Value);
        Assert.Equal("new-desc", result.Description);
        _configurationRepository.Verify(r => r.UpdateAsync(existing), Times.Once);
    }

    [Fact]
    public async Task DeleteAsync_DelegatesToRepository()
    {
        _configurationRepository.Setup(r => r.DeleteAsync("app-1", "key-a")).ReturnsAsync(true);

        var result = await _service.DeleteAsync("app-1", "key-a");

        Assert.True(result);
    }
}
