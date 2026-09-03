using Moq;

namespace ConfigApi.Service.UnitTests.Services;

public class ApplicationServiceTests
{
    private readonly Mock<IApplicationRepository> _applicationRepository = new();
    private readonly Mock<IConfigurationRepository> _configurationRepository = new();
    private readonly ApplicationService _service;

    public ApplicationServiceTests()
    {
        _service = new ApplicationService(_applicationRepository.Object, _configurationRepository.Object);
    }

    [Fact]
    public async Task CreateAsync_Throws_WhenNameAlreadyExists()
    {
        var existing = new Application { Id = "1", Name = "Existing App" };
        _applicationRepository.Setup(r => r.GetByName("Existing App")).Returns(existing);

        var newApplication = new Application { Name = "Existing App" };

        await Assert.ThrowsAsync<DuplicateApplicationNameException>(
            () => _service.CreateAsync(newApplication));

        _applicationRepository.Verify(r => r.CreateAsync(It.IsAny<Application>()), Times.Never);
    }

    [Fact]
    public async Task CreateAsync_Succeeds_WhenNameIsNew()
    {
        _applicationRepository.Setup(r => r.GetByName("New App")).Returns((Application?)null);
        _applicationRepository
            .Setup(r => r.CreateAsync(It.IsAny<Application>()))
            .ReturnsAsync((Application a) => a);

        var newApplication = new Application { Name = "New App" };

        var result = await _service.CreateAsync(newApplication);

        Assert.Equal("New App", result.Name);
        Assert.False(string.IsNullOrWhiteSpace(result.Id));
        _applicationRepository.Verify(r => r.CreateAsync(It.IsAny<Application>()), Times.Once);
    }

    [Fact]
    public async Task UpdateAsync_ReturnsNull_WhenApplicationDoesNotExist()
    {
        _applicationRepository.Setup(r => r.GetById("missing")).Returns((Application?)null);

        var result = await _service.UpdateAsync("missing", new Application { Name = "New Name" });

        Assert.Null(result);
        _applicationRepository.Verify(r => r.UpdateAsync(It.IsAny<Application>()), Times.Never);
    }

    [Fact]
    public async Task UpdateAsync_UpdatesNameAndDescription_WhenApplicationExists()
    {
        var existing = new Application { Id = "1", Name = "Old Name", Description = "Old" };
        _applicationRepository.Setup(r => r.GetById("1")).Returns(existing);
        _applicationRepository.Setup(r => r.UpdateAsync(It.IsAny<Application>())).ReturnsAsync(true);

        var result = await _service.UpdateAsync("1", new Application { Name = "New Name", Description = "New" });

        Assert.NotNull(result);
        Assert.Equal("New Name", result!.Name);
        Assert.Equal("New", result.Description);
        _applicationRepository.Verify(r => r.UpdateAsync(existing), Times.Once);
    }

    [Fact]
    public async Task DeleteAsync_ReturnsNull_WhenApplicationDoesNotExist()
    {
        _applicationRepository.Setup(r => r.GetById("missing")).Returns((Application?)null);

        var result = await _service.DeleteAsync("missing");

        Assert.Null(result);
    }

    [Fact]
    public async Task DeleteAsync_ReturnsFalse_WhenConfigurationsExist()
    {
        var application = new Application { Id = "1", Name = "App" };
        _applicationRepository.Setup(r => r.GetById("1")).Returns(application);
        _configurationRepository
            .Setup(r => r.GetAllForApplication("1"))
            .Returns([new Configuration { ApplicationId = "1", ConfigKey = "key" }]);

        var result = await _service.DeleteAsync("1");

        Assert.False(result);
        _applicationRepository.Verify(r => r.DeleteAsync(It.IsAny<string>()), Times.Never);
    }

    [Fact]
    public async Task DeleteAsync_ReturnsTrue_WhenNoConfigurationsExist()
    {
        var application = new Application { Id = "1", Name = "App" };
        _applicationRepository.Setup(r => r.GetById("1")).Returns(application);
        _configurationRepository.Setup(r => r.GetAllForApplication("1")).Returns([]);
        _applicationRepository.Setup(r => r.DeleteAsync("1")).ReturnsAsync(true);

        var result = await _service.DeleteAsync("1");

        Assert.True(result);
    }
}
