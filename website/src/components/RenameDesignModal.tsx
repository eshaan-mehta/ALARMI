import { useEffect } from 'react';
import { Button, Group, Modal, Stack, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { isAxiosError } from 'axios';
import { useUpdateDesign } from '../data/designs/hooks';
import type { Design } from '../data/designs/types';

interface Props {
  design: Design;
  projectId: string;
  opened: boolean;
  onClose: () => void;
}

export function RenameDesignModal({ design, projectId, opened, onClose }: Props) {
  const update = useUpdateDesign(projectId);

  const form = useForm({
    initialValues: { name: design.name },
    validate: {
      name: (v) => (v.trim().length === 0 ? 'Design name is required' : null),
    },
  });

  // Re-seed with the current name each time the modal opens.
  useEffect(() => {
    if (opened) form.setValues({ name: design.name });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opened]);

  const handleClose = () => {
    if (update.isPending) return;
    onClose();
  };

  const handleSubmit = form.onSubmit((values) => {
    update.mutate(
      { designId: design.designId, patch: { name: values.name.trim() } },
      {
        onSuccess: (d) => {
          notifications.show({
            color: 'teal',
            title: 'Design renamed',
            message: `Renamed to “${d.name}”.`,
          });
          onClose();
        },
        onError: (err) => {
          const message = isAxiosError(err)
            ? (err.response?.data?.message ?? 'Could not rename design.')
            : 'Could not rename design.';
          notifications.show({ color: 'red', title: 'Rename failed', message });
        },
      },
    );
  });

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title="Rename design"
      centered
      closeOnClickOutside={!update.isPending}
    >
      <form onSubmit={handleSubmit}>
        <Stack>
          <TextInput label="Design name" data-autofocus {...form.getInputProps('name')} />
          <Group justify="flex-end">
            <Button variant="default" onClick={handleClose} disabled={update.isPending}>
              Cancel
            </Button>
            <Button type="submit" loading={update.isPending}>
              Save
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
