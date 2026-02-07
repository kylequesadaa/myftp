# How to Test the FTP Client

## Running the Client

From the project directory, run:

```
python myftp.py inet.cs.fiu.edu
```

## Login Credentials

- Username: `demo`
- Password: `demopass`

## Testing Commands

Once logged in, try these commands in order:

1. **`ls`** — List files on the server to see what's available
2. **`get <filename>`** — Pick a file from the `ls` output (e.g. `get test.txt`)
3. **`put readme.txt`** — Upload your local readme.txt to the server
4. **`ls`** — Verify the uploaded file appears
5. **`quit`** — Disconnect

You should see success/failure messages and byte counts after each transfer. The downloaded file will appear in your current working directory.
