using Moq;

namespace ConfigApi.Service.UnitTests.Services;

public class FlagServiceTests
{
    private readonly Mock<IFlagRepository> _flagRepository = new();
    private readonly Mock<IApplicationRepository> _applicationRepository = new();
    private readonly FlagService _service;

    public FlagServiceTests()
    {
        _service = new FlagService(_flagRepository.Object, _applicationRepository.Object);
    }

    [Fact]
    public async Task CreateAsync_Throws_ApplicationNotFoundException_WhenParentApplicationMissing()
    {
        _applicationRepository.Setup(r => r.GetById("app-1")).Returns((Application?)null);

        var flag = new Flag { FlagKey = "flag-a", Enabled = true };

        await Assert.ThrowsAsync<ApplicationNotFoundException>(
            () => _service.CreateAsync("app-1", flag));
    }

    [Fact]
    public async Task CreateAsync_Throws_DuplicateFlagKeyException_OnSecondCreateWithSameKey()
    {
        var application = new Application { Id = "app-1", Name = "App" };
        _applicationRepository.Setup(r => r.GetById("app-1")).Returns(application);
        _flagRepository
            .Setup(r => r.GetByKey("app-1", "flag-a"))
            .Returns(new Flag { ApplicationId = "app-1", FlagKey = "flag-a" });

        var flag = new Flag { FlagKey = "flag-a", Enabled = true };

        await Assert.ThrowsAsync<DuplicateFlagKeyException>(
            () => _service.CreateAsync("app-1", flag));
    }

    [Fact]
    public async Task CreateAsync_Throws_ValidationException_WhenFlagKeyIsInvalid()
    {
        var application = new Application { Id = "app-1", Name = "App" };
        _applicationRepository.Setup(r => r.GetById("app-1")).Returns(application);

        var flag = new Flag { FlagKey = "invalid/key", Enabled = true };

        await Assert.ThrowsAsync<ValidationException>(
            () => _service.CreateAsync("app-1", flag));
    }

    [Fact]
    public async Task CreateAsync_PropagatesValidCreate()
    {
        var application = new Application { Id = "app-1", Name = "App" };
        _applicationRepository.Setup(r => r.GetById("app-1")).Returns(application);
        _flagRepository.Setup(r => r.GetByKey("app-1", "flag-a")).Returns((Flag?)null);
        _flagRepository
            .Setup(r => r.CreateAsync(It.IsAny<Flag>()))
            .ReturnsAsync((Flag f) => f);

        var flag = new Flag { FlagKey = "flag-a", Enabled = true };

        var result = await _service.CreateAsync("app-1", flag);

        Assert.Equal("app-1", result.ApplicationId);
        Assert.Equal("flag-a", result.FlagKey);
        _flagRepository.Verify(r => r.CreateAsync(It.IsAny<Flag>()), Times.Once);
    }

    [Fact]
    public async Task UpdateAsync_ReturnsNull_WhenFlagDoesNotExist()
    {
        _flagRepository.Setup(r => r.GetByKey("app-1", "flag-a")).Returns((Flag?)null);

        var result = await _service.UpdateAsync("app-1", "flag-a", new Flag { Enabled = false });

        Assert.Null(result);
    }

    [Fact]
    public async Task UpdateAsync_UpdatesEnabledAndDescription_WhenFlagExists()
    {
        var existing = new Flag { ApplicationId = "app-1", FlagKey = "flag-a", Enabled = false, Description = "old-desc" };
        _flagRepository.Setup(r => r.GetByKey("app-1", "flag-a")).Returns(existing);
        _flagRepository.Setup(r => r.UpdateAsync(It.IsAny<Flag>())).ReturnsAsync(true);

        var result = await _service.UpdateAsync("app-1", "flag-a", new Flag { Enabled = true, Description = "new-desc" });

        Assert.NotNull(result);
        Assert.True(result!.Enabled);
        Assert.Equal("new-desc", result.Description);
        _flagRepository.Verify(r => r.UpdateAsync(existing), Times.Once);
    }

    [Fact]
    public async Task DeleteAsync_DelegatesToRepository()
    {
        _flagRepository.Setup(r => r.DeleteAsync("app-1", "flag-a")).ReturnsAsync(true);

        var result = await _service.DeleteAsync("app-1", "flag-a");

        Assert.True(result);
    }
}
