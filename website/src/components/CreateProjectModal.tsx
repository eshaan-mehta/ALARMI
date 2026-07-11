import { Button, Group, Modal, Stack, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { isAxiosError } from 'axios';
import { useNavigate } from 'react-router-dom';
import { useCreateProject } from '../data/projects/hooks';

interface Props {
  opened: boolean;
  onClose: () => void;
}

export function CreateProjectModal({ opened, onClose }: Props) {
  const navigate = useNavigate();
  const createProject = useCreateProject();

  const form = useForm({
    initialValues: { name: '' },
    validate: {
      name: (v) => (v.trim().length === 0 ? 'Project name is required' : null),
    },
  });

  const handleClose = () => {
    form.reset();
    onClose();
  };

  const handleSubmit = form.onSubmit((values) => {
    createProject.mutate(values.name.trim(), {
      onSuccess: (project) => {
        notifications.show({
          color: 'teal',
          title: 'Project created',
          message: `“${project.name}” is ready for designs.`,
        });
        handleClose();
        navigate(`/projects/${encodeURIComponent(project.name)}`);
      },
      onError: (err) => {
        const message = isAxiosError(err)
          ? (err.response?.data?.message ?? 'Could not create project.')
          : 'Could not create project.';
        form.setFieldError('name', message);
      },
    });
  });

  return (
    <Modal opened={opened} onClose={handleClose} title="Create project" centered>
      <form onSubmit={handleSubmit}>
        <Stack>
          <TextInput
            label="Project name"
            placeholder="e.g. Riverside Modular Clinic"
            data-autofocus
            {...form.getInputProps('name')}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" loading={createProject.isPending}>
              Create
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
