using System.Text.Json;
using ConfigApi.Service.Middleware;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging.Abstractions;

namespace ConfigApi.Service.UnitTests.Middleware;

public class ErrorMiddlewareTests
{
    private static async Task<(int StatusCode, JsonElement Body)> InvokeAsync(Exception exception)
    {
        var context = new DefaultHttpContext();
        context.Response.Body = new MemoryStream();

        var middleware = new ErrorMiddleware(_ => throw exception, NullLogger<ErrorMiddleware>.Instance);

        await middleware.InvokeAsync(context);

        context.Response.Body.Seek(0, SeekOrigin.Begin);
        using var reader = new StreamReader(context.Response.Body);
        var json = await reader.ReadToEndAsync();
        var body = JsonDocument.Parse(json).RootElement.Clone();

        return (context.Response.StatusCode, body);
    }

    [Fact]
    public async Task ApplicationNotFoundException_MapsTo404()
    {
        var (statusCode, body) = await InvokeAsync(new ApplicationNotFoundException("Application 'x' was not found."));

        Assert.Equal(StatusCodes.Status404NotFound, statusCode);
        Assert.Equal("ApplicationNotFoundException", body.GetProperty("exceptionType").GetString());
    }

    [Fact]
    public async Task ConfigurationNotFoundException_MapsTo404()
    {
        var (statusCode, body) = await InvokeAsync(new ConfigurationNotFoundException("Configuration key 'x' was not found."));

        Assert.Equal(StatusCodes.Status404NotFound, statusCode);
        Assert.Equal("ConfigurationNotFoundException", body.GetProperty("exceptionType").GetString());
    }

    [Fact]
    public async Task DuplicateApplicationNameException_MapsTo409()
    {
        var (statusCode, body) = await InvokeAsync(new DuplicateApplicationNameException("An application named 'x' already exists."));

        Assert.Equal(StatusCodes.Status409Conflict, statusCode);
        Assert.Equal("DuplicateApplicationNameException", body.GetProperty("exceptionType").GetString());
    }

    [Fact]
    public async Task DuplicateConfigurationKeyException_MapsTo409()
    {
        var (statusCode, body) = await InvokeAsync(new DuplicateConfigurationKeyException("Configuration key 'x' already exists."));

        Assert.Equal(StatusCodes.Status409Conflict, statusCode);
        Assert.Equal("DuplicateConfigurationKeyException", body.GetProperty("exceptionType").GetString());
    }

    [Fact]
    public async Task ValidationException_MapsTo400_AndIncludesErrors()
    {
        var errors = new Dictionary<string, string> { ["configKey"] = "Must contain only letters, digits, '.', '_' or '-'." };
        var (statusCode, body) = await InvokeAsync(new ValidationException("Configuration key is invalid.", errors));

        Assert.Equal(StatusCodes.Status400BadRequest, statusCode);
        Assert.Equal("ValidationException", body.GetProperty("exceptionType").GetString());
        Assert.True(body.GetProperty("error").TryGetProperty("configKey", out _));
    }

    [Fact]
    public async Task ArgumentException_MapsTo400()
    {
        var (statusCode, body) = await InvokeAsync(new ArgumentException("bad argument"));

        Assert.Equal(StatusCodes.Status400BadRequest, statusCode);
        Assert.Equal("ArgumentException", body.GetProperty("exceptionType").GetString());
    }

    [Fact]
    public async Task UnhandledException_MapsTo500_WithGenericDetail()
    {
        var (statusCode, body) = await InvokeAsync(new InvalidOperationException("something internal broke"));

        Assert.Equal(StatusCodes.Status500InternalServerError, statusCode);
        Assert.Equal("An unexpected error occurred.", body.GetProperty("detail").GetString());
    }
}
