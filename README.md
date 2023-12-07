# telecrawler
A random telegram crawler that is able to save groups messages, files, images, and relations users/groups. Sqlite is used for storage. This little project can be used to gather OSINT information.

Try not to push the limits too much, or telegram will block your user for a little while. Do not use your personal account.

Features and change requests are welcome.

Future work:
* Extract links while crawling, and store them in a separate table.
* Include date when message was sent and the date it was crawled.
* Improve exception/error handling.
* Chose another data storage method so concurrent crawlers can be run with different users.
* In some specific conditions, robot asks to join private groups, copy messages and leave.
