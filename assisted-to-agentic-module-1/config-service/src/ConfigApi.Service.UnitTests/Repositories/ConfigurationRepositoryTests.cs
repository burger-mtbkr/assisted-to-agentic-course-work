using ConfigApi.Service.Infrastructure.DynamoDb;
using Moq;

namespace ConfigApi.Service.UnitTests.Repositories;

public class ConfigurationRepositoryTests
{
    private static (ConfigurationRepository Repo, Mock<IDynamoDbCompositeKeyCollection<Configuration>> Collection) CreateRepo()
    {
        var collection = new Mock<IDynamoDbCompositeKeyCollection<Configuration>>();
        var repo = new ConfigurationRepository(collection.Object);
        return (repo, collection);
    }

    [Fact]
    public void GetAllForApplication_ReturnsOnlyMatchingApplicationId()
    {
        var (repo, collection) = CreateRepo();
        var configurations = new List<Configuration>
        {
            new() { ApplicationId = "app-1", ConfigKey = "key-a" },
            new() { ApplicationId = "app-2", ConfigKey = "key-b" }
        };
        collection.Setup(c => c.AsQueryable()).Returns(configurations.AsQueryable());

        var result = repo.GetAllForApplication("app-1");

        var configuration = Assert.Single(result);
        Assert.Equal("key-a", configuration.ConfigKey);
    }

    [Fact]
    public void GetByKey_DelegatesToCollection()
    {
        var (repo, collection) = CreateRepo();
        var configuration = new Configuration { ApplicationId = "app-1", ConfigKey = "key-a" };
        collection.Setup(c => c.GetByKey("app-1", "key-a")).Returns(configuration);

        var result = repo.GetByKey("app-1", "key-a");

        Assert.Same(configuration, result);
    }

    [Fact]
    public async Task CreateAsync_InsertsAndReturnsConfiguration()
    {
        var (repo, collection) = CreateRepo();
        var configuration = new Configuration { ApplicationId = "app-1", ConfigKey = "key-a" };

        var result = await repo.CreateAsync(configuration);

        collection.Verify(c => c.InsertOneAsync(configuration), Times.Once);
        Assert.Same(configuration, result);
    }

    [Fact]
    public async Task UpdateAsync_DelegatesToCollectionReplaceOneAsync()
    {
        var (repo, collection) = CreateRepo();
        var configuration = new Configuration { ApplicationId = "app-1", ConfigKey = "key-a" };
        collection.Setup(c => c.ReplaceOneAsync(configuration, false)).ReturnsAsync(true);

        var result = await repo.UpdateAsync(configuration);

        Assert.True(result);
        collection.Verify(c => c.ReplaceOneAsync(configuration, false), Times.Once);
    }

    [Fact]
    public async Task DeleteAsync_DelegatesToCollectionDeleteOneAsync()
    {
        var (repo, collection) = CreateRepo();
        collection.Setup(c => c.DeleteOneAsync("app-1", "key-a")).ReturnsAsync(true);

        var result = await repo.DeleteAsync("app-1", "key-a");

        Assert.True(result);
        collection.Verify(c => c.DeleteOneAsync("app-1", "key-a"), Times.Once);
    }
}
