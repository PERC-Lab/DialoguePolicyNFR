def assign_batches_to_user(uuid):

    assignments = {
        "48b181c2-0689-4a5b-9d61-0644f4e37492": [
            1
        ],
        "process-1768508305789-14650": [
            1
        ],
        "03da7645-232c-429c-be02-389a00eb33c0": [
            2
        ],
        "2dee0f05-c597-432b-9d5e-1cf938fb436c": [
            2
        ],
        "efdd096c-7cc5-429c-ad81-99af13f7c20d": [
            3
        ],
        "1ce0ca00-a660-4d8d-bb92-55aa138a495c": [
            3
        ],
        "debf8256-4dbc-4f71-972d-89488d17a8b1": [
            4
        ],
        "e7c3d057-f0bb-4f30-aea0-ab689f9412ac": [
            1
        ]
        }

    if uuid in assignments:
        return assignments[uuid]

    total_batches = 19

    batch_user_count = {}
    for user_uuid, user_batches in assignments.items():
        for batch_num in user_batches:
            batch_user_count[batch_num] = batch_user_count.get(batch_num, 0) + 1

    # First available batch: lowest batch number that has fewer than 2 users
    selected_batch = None
    for batch_num in range(1, total_batches + 1):
        if batch_user_count.get(batch_num, 0) < 2:
            selected_batch = batch_num
            break

    if selected_batch is None:
        selected_batch = 1

    assigned = [selected_batch]
    assignments[uuid] = assigned
    return assigned, assignments

a, b= assign_batches_to_user("new")
print(a)
print(b)