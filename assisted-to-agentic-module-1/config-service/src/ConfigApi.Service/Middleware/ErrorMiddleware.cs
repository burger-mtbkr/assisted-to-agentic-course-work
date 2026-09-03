namespace ConfigApi.Service.Middleware;

public class ErrorMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<ErrorMiddleware> _logger;

    public ErrorMiddleware(RequestDelegate next, ILogger<ErrorMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        try
        {
            await _next(context);
        }
        catch (ApplicationNotFoundException ex)
        {
            await WriteResponseAsync(context, StatusCodes.Status404NotFound, "Not Found", ex.Message, ex);
        }
        catch (ConfigurationNotFoundException ex)
        {
            await WriteResponseAsync(context, StatusCodes.Status404NotFound, "Not Found", ex.Message, ex);
        }
        catch (DuplicateApplicationNameException ex)
        {
            await WriteResponseAsync(context, StatusCodes.Status409Conflict, "Conflict", ex.Message, ex);
        }
        catch (DuplicateConfigurationKeyException ex)
        {
            await WriteResponseAsync(context, StatusCodes.Status409Conflict, "Conflict", ex.Message, ex);
        }
        catch (ValidationException ex)
        {
            await WriteResponseAsync(context, StatusCodes.Status400BadRequest, "Bad Request", ex.Message, ex, ex.Errors);
        }
        catch (ArgumentException ex)
        {
            await WriteResponseAsync(context, StatusCodes.Status400BadRequest, "Bad Request", ex.Message, ex);
        }
        catch (Exception ex)
        {
            await WriteResponseAsync(
                context,
                StatusCodes.Status500InternalServerError,
                "Internal Server Error",
                "An unexpected error occurred.",
                ex);
        }
    }

    private async Task WriteResponseAsync(
        HttpContext context,
        int statusCode,
        string title,
        string detail,
        Exception exception,
        IReadOnlyDictionary<string, string>? errors = null)
    {
        _logger.LogError(exception, "Request failed with status {StatusCode}: {Message}", statusCode, exception.Message);

        context.Response.ContentType = "application/json";
        context.Response.StatusCode = statusCode;

        var body = new
        {
            status = statusCode,
            title,
            detail,
            error = errors,
            exceptionType = exception.GetType().Name,
            traceId = context.TraceIdentifier
        };

        await context.Response.WriteAsJsonAsync(body);
    }
}
