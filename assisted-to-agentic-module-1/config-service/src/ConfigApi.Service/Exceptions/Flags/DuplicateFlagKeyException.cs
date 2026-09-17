namespace ConfigApi.Service.Exceptions.Flags;

public class DuplicateFlagKeyException : Exception
{
    public DuplicateFlagKeyException(string message)
        : base(message)
    {
    }
}
