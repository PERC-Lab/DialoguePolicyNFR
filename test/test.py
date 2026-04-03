def assign_batches_to_user(uuid):

    assignments = {
  "232fb27e-b2ad-4862-b574-c27dc374b6b0": [
    2
  ],
  "932fb27e-b2ad-4862-b574-c27dc374b6b0": [
    2
  ],

  "e9d46a67-49a6-445b-a851-46effd7e101c": [
    9
  ],
  "919e13b3-57c3-46bf-8496-ef7ab7db8eba": [
    9
  ],
}

    if uuid in assignments:
        return assignments[uuid]

    total_batches = 19

    batch_user_count = {}
    for user_uuid, user_batches in assignments.items():
        for batch_num in user_batches:
            batch_user_count[batch_num] = batch_user_count.get(batch_num, 0) + 1

    preferred_batches = [2, 9,]
    candidate_batches = [
        b for b in preferred_batches if 1 <= b <= total_batches
    ] + [
        b for b in range(1, total_batches + 1) if b not in preferred_batches
    ]

    selected_batch = None
    for batch_num in candidate_batches:
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