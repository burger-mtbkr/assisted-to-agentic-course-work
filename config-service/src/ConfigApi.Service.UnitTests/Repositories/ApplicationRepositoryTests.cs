using ConfigApi.Service.Infrastructure.DynamoDb;
using Moq;

namespace ConfigApi.Service.UnitTests.Repositories;

public class ApplicationRepositoryTests
{
    private static (ApplicationRepository Repo, Mock<IDynamoDbCollection<Application>> Collection) CreateRepo()
    {
        var collection = new Mock<IDynamoDbCollection<Application>>();
        var repo = new ApplicationRepository(collection.Object);
        return (repo, collection);
    }

    [Fact]
    public void GetAll_ReturnsAllItemsFromCollection()
    {
        var (repo, collection) = CreateRepo();
        var applications = new List<Application>
        {
            new() { Id = "1", Name = "App One" },
            new() { Id = "2", Name = "App Two" }
        };
        collection.Setup(c => c.AsQueryable()).Returns(applications.AsQueryable());

        var result = repo.GetAll();

        Assert.Equal(2, result.Count);
    }

    [Fact]
    public void GetById_ReturnsItem_WhenFound()
    {
        var (repo, collection) = CreateRepo();
        var application = new Application { Id = "1", Name = "App One" };
        collection.Setup(c => c.GetById("1")).Returns(application);

        var result = repo.GetById("1");

        Assert.Same(application, result);
    }

    [Fact]
    public void GetByName_ReturnsMatch_WhenNameExists()
    {
        var (repo, collection) = CreateRepo();
        var applications = new List<Application>
        {
            new() { Id = "1", Name = "App One" },
            new() { Id = "2", Name = "App Two" }
        };
        collection.Setup(c => c.AsQueryable()).Returns(applications.AsQueryable());

        var result = repo.GetByName("App Two");

        Assert.NotNull(result);
        Assert.Equal("2", result!.Id);
    }

    [Fact]
    public void GetByName_ReturnsNull_WhenNameDoesNotExist()
    {
        var (repo, collection) = CreateRepo();
        var applications = new List<Application>
        {
            new() { Id = "1", Name = "App One" }
        };
        collection.Setup(c => c.AsQueryable()).Returns(applications.AsQueryable());

        var result = repo.GetByName("Nonexistent");

        Assert.Null(result);
    }

    [Fact]
    public async Task CreateAsync_InsertsAndReturnsApplication()
    {
        var (repo, collection) = CreateRepo();
        var application = new Application { Id = "1", Name = "App One" };

        var result = await repo.CreateAsync(application);

        collection.Verify(c => c.InsertOneAsync(application), Times.Once);
        Assert.Same(application, result);
    }

    [Fact]
    public async Task UpdateAsync_DelegatesToCollectionReplaceOneAsync()
    {
        var (repo, collection) = CreateRepo();
        var application = new Application { Id = "1", Name = "App One" };
        collection.Setup(c => c.ReplaceOneAsync(application, false)).ReturnsAsync(true);

        var result = await repo.UpdateAsync(application);

        Assert.True(result);
        collection.Verify(c => c.ReplaceOneAsync(application, false), Times.Once);
    }

    [Fact]
    public async Task DeleteAsync_DelegatesToCollectionDeleteOneAsync()
    {
        var (repo, collection) = CreateRepo();
        collection.Setup(c => c.DeleteOneAsync("1")).ReturnsAsync(true);

        var result = await repo.DeleteAsync("1");

        Assert.True(result);
        collection.Verify(c => c.DeleteOneAsync("1"), Times.Once);
    }
}
