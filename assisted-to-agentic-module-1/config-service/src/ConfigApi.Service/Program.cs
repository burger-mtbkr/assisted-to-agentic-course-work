using ConfigApi.Service.Ignition;
using ConfigApi.Service.Middleware;
using Scalar.AspNetCore;
using Serilog;

DotNetEnv.Env.Load();

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddOpenApi();

builder.ConfigureLogging();
builder.ConfigureDynamoDb();
builder.Services.ConfigureRepositories();
builder.Services.ConfigureServices();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
    app.MapScalarApiReference();
    app.MapGet("/", () => Results.Redirect("/scalar")).ExcludeFromDescription();
}

app.UseSerilogRequestLogging();
app.UseMiddleware<ErrorMiddleware>();
app.MapControllers();

app.Run();
