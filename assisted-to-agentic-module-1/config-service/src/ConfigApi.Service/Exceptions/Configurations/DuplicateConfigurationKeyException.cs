namespace ConfigApi.Service.Exceptions.Configurations;

public class DuplicateConfigurationKeyException : Exception
{
    public DuplicateConfigurationKeyException(string message)
        : base(message)
    {
    }
}
