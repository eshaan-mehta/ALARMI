import { useEffect } from 'react';
import { Button, Group, Modal, Stack, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { isAxiosError } from 'axios';
import { useRenameProject } from '../data/projects/hooks';
import type { Project } from '../data/projects/types';

interface Props {
  project: Project;
  opened: boolean;
  onClose: () => void;
}

export function RenameProjectModal({ project, opened, onClose }: Props) {
  const rename = useRenameProject();

  const form = useForm({
    initialValues: { name: project.name },
    validate: {
      name: (v) => (v.trim().length === 0 ? 'Project name is required' : null),
    },
  });

  // Re-seed with the current name each time the modal opens.
  useEffect(() => {
    if (opened) form.setValues({ name: project.name });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opened]);

  const handleClose = () => {
    if (rename.isPending) return;
    onClose();
  };

  const handleSubmit = form.onSubmit((values) => {
    const newName = values.name.trim();
    if (newName === project.name) {
      onClose();
      return;
    }
    rename.mutate(
      { projectId: project.projectId, newName },
      {
        onSuccess: (p) => {
          notifications.show({
            color: 'teal',
            title: 'Project renamed',
            message: `Renamed to “${p.name}”.`,
          });
          onClose();
        },
        onError: (err) => {
          const message = isAxiosError(err)
            ? (err.response?.data?.message ?? 'Could not rename project.')
            : 'Could not rename project.';
          form.setFieldError('name', message);
        },
      },
    );
  });

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title="Rename project"
      centered
      closeOnClickOutside={!rename.isPending}
    >
      <form onSubmit={handleSubmit}>
        <Stack>
          <TextInput label="Project name" data-autofocus {...form.getInputProps('name')} />
          <Group justify="flex-end">
            <Button variant="default" onClick={handleClose} disabled={rename.isPending}>
              Cancel
            </Button>
            <Button type="submit" loading={rename.isPending}>
              Save
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
