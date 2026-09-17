using ConfigApi.Service.Infrastructure.DynamoDb;
using Moq;

namespace ConfigApi.Service.UnitTests.Repositories;

public class FlagRepositoryTests
{
    private static (FlagRepository Repo, Mock<IDynamoDbCompositeKeyCollection<Flag>> Collection) CreateRepo()
    {
        var collection = new Mock<IDynamoDbCompositeKeyCollection<Flag>>();
        var repo = new FlagRepository(collection.Object);
        return (repo, collection);
    }

    [Fact]
    public void GetAllForApplication_ReturnsOnlyMatchingApplicationId()
    {
        var (repo, collection) = CreateRepo();
        var flags = new List<Flag>
        {
            new() { ApplicationId = "app-1", FlagKey = "flag-a" },
            new() { ApplicationId = "app-2", FlagKey = "flag-b" }
        };
        collection.Setup(c => c.AsQueryable()).Returns(flags.AsQueryable());

        var result = repo.GetAllForApplication("app-1");

        var flag = Assert.Single(result);
        Assert.Equal("flag-a", flag.FlagKey);
    }

    [Fact]
    public void GetByKey_DelegatesToCollection()
    {
        var (repo, collection) = CreateRepo();
        var flag = new Flag { ApplicationId = "app-1", FlagKey = "flag-a" };
        collection.Setup(c => c.GetByKey("app-1", "flag-a")).Returns(flag);

        var result = repo.GetByKey("app-1", "flag-a");

        Assert.Same(flag, result);
    }

    [Fact]
    public async Task CreateAsync_InsertsAndReturnsFlag()
    {
        var (repo, collection) = CreateRepo();
        var flag = new Flag { ApplicationId = "app-1", FlagKey = "flag-a" };

        var result = await repo.CreateAsync(flag);

        collection.Verify(c => c.InsertOneAsync(flag), Times.Once);
        Assert.Same(flag, result);
    }

    [Fact]
    public async Task UpdateAsync_DelegatesToCollectionReplaceOneAsync()
    {
        var (repo, collection) = CreateRepo();
        var flag = new Flag { ApplicationId = "app-1", FlagKey = "flag-a" };
        collection.Setup(c => c.ReplaceOneAsync(flag, false)).ReturnsAsync(true);

        var result = await repo.UpdateAsync(flag);

        Assert.True(result);
        collection.Verify(c => c.ReplaceOneAsync(flag, false), Times.Once);
    }

    [Fact]
    public async Task DeleteAsync_DelegatesToCollectionDeleteOneAsync()
    {
        var (repo, collection) = CreateRepo();
        collection.Setup(c => c.DeleteOneAsync("app-1", "flag-a")).ReturnsAsync(true);

        var result = await repo.DeleteAsync("app-1", "flag-a");

        Assert.True(result);
        collection.Verify(c => c.DeleteOneAsync("app-1", "flag-a"), Times.Once);
    }
}
