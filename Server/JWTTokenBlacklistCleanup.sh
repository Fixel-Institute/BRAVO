# Guide from https://stackoverflow.com/a/29577063

USERNAME=BRAVOAdmin
PASSWORD=AdminPassword
DATABASE=BRAVOServer
MYSQL=/usr/bin/mysql

$MYSQL -u $USERNAME -p$PASSWORD $DATABASE -e "DELETE from token_blacklist_blacklistedtoken;"
$MYSQL -u $USERNAME -p$PASSWORD $DATABASE -e "DELETE FROM token_blacklist_outstandingtoken WHERE expires_at < NOW();"