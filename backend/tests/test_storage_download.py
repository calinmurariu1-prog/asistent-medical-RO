"""Original downloads close storage streams and sanitize recoverable failures."""
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from app.services.storage import S3Storage


def _storage():
    storage = object.__new__(S3Storage)
    storage._bucket = "synthetic-bucket"
    storage._client = Mock()
    return storage


@pytest.mark.parametrize("failure", [False, True])
def test_s3_stream_is_closed_even_when_read_fails(failure):
    storage = _storage()
    body = Mock()
    body.read.return_value = b"synthetic-original"
    if failure:
        body.read.side_effect = TimeoutError("private-provider-detail")
    storage._client.get_object.return_value = {"Body": body}
    if failure:
        with pytest.raises(TimeoutError):
            storage.get("synthetic-key")
    else:
        assert storage.get("synthetic-key") == b"synthetic-original"
    body.close.assert_called_once()


@pytest.mark.parametrize("code", ["NoSuchKey", "NotFound", "404", "AccessDenied"])
def test_s3_missing_object_does_not_misclassify_permission_errors(code):
    storage = _storage()
    storage._client.get_object.side_effect = ClientError(
        {"Error": {"Code": code, "Message": "private-provider-detail"}}, "GetObject")
    expected = ClientError if code == "AccessDenied" else FileNotFoundError
    with pytest.raises(expected):
        storage.get("synthetic-key")
