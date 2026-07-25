import { useState } from 'react';
import {
  Button,
  Group,
  Modal,
  Progress,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
} from '@mantine/core';
import { Dropzone } from '@mantine/dropzone';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import {
  IconFile3d,
  IconUpload,
  IconX,
} from '@tabler/icons-react';
import { isAxiosError } from 'axios';
import { formatBytes } from '../lib/format';
import { useUploadDesign } from '../data/designs/hooks';

interface Props {
  projectId: string;
  opened: boolean;
  onClose: () => void;
}

const MAX_BYTES = 1024 ** 3; // 1 GB

export function UploadModal({ projectId, opened, onClose }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const upload = useUploadDesign(projectId);

  const form = useForm({
    initialValues: { name: '' },
    validate: {
      name: (v) => (v.trim().length === 0 ? 'Design name is required' : null),
    },
  });

  const reset = () => {
    form.reset();
    setFile(null);
    setProgress(0);
  };

  const handleClose = () => {
    if (upload.isPending) return; // don't close mid-upload
    reset();
    onClose();
  };

  const handleDrop = (files: File[]) => {
    const dropped = files[0];
    if (!dropped) return;
    if (!dropped.name.toLowerCase().endsWith('.ifc')) {
      notifications.show({
        color: 'red',
        title: 'Invalid file',
        message: 'Only .ifc design files are accepted.',
      });
      return;
    }
    if (dropped.size > MAX_BYTES) {
      notifications.show({
        color: 'red',
        title: 'File too large',
        message: 'The maximum file size is 1 GB.',
      });
      return;
    }
    setFile(dropped);
    // Prefill the name from the file if the user hasn't typed one.
    if (!form.values.name.trim()) {
      form.setFieldValue('name', dropped.name.replace(/\.ifc$/i, ''));
    }
  };

  const handleSubmit = form.onSubmit((values) => {
    if (!file) {
      notifications.show({
        color: 'red',
        title: 'No file selected',
        message: 'Add an .ifc file before uploading.',
      });
      return;
    }
    setProgress(0);
    upload.mutate(
      { name: values.name.trim(), file, onProgress: setProgress },
      {
        onSuccess: (design) => {
          notifications.show({
            color: 'teal',
            title: 'Upload complete',
            message: `“${design.name}” is now processing.`,
          });
          reset();
          onClose();
        },
        onError: (err) => {
          const message = isAxiosError(err)
            ? (err.response?.data?.message ?? 'Upload failed.')
            : 'Upload failed.';
          notifications.show({ color: 'red', title: 'Upload failed', message });
        },
      },
    );
  });

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title="Upload design"
      centered
      closeOnClickOutside={!upload.isPending}
    >
      <form onSubmit={handleSubmit}>
        <Stack>
          <TextInput
            label="Design name"
            placeholder="e.g. Ward A Headwall"
            data-autofocus
            {...form.getInputProps('name')}
          />

          {file ? (
            <Group
              justify="space-between"
              p="sm"
              style={{
                border: '1px solid var(--mantine-color-default-border)',
                borderRadius: 'var(--mantine-radius-md)',
              }}
            >
              <Group gap="sm" wrap="nowrap">
                <ThemeIcon variant="light" size="lg" radius="md">
                  <IconFile3d size={20} />
                </ThemeIcon>
                <div>
                  <Text size="sm" fw={500} lineClamp={1}>
                    {file.name}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {formatBytes(file.size)}
                  </Text>
                </div>
              </Group>
              {!upload.isPending && (
                <Button
                  variant="subtle"
                  color="gray"
                  size="compact-sm"
                  onClick={() => setFile(null)}
                >
                  Remove
                </Button>
              )}
            </Group>
          ) : (
            <Dropzone
              onDrop={handleDrop}
              maxSize={MAX_BYTES}
              multiple={false}
              disabled={upload.isPending}
            >
              <Stack align="center" gap={6} py="lg" style={{ pointerEvents: 'none' }}>
                <Dropzone.Accept>
                  <IconUpload size={40} color="var(--mantine-color-violet-6)" />
                </Dropzone.Accept>
                <Dropzone.Reject>
                  <IconX size={40} color="var(--mantine-color-red-6)" />
                </Dropzone.Reject>
                <Dropzone.Idle>
                  <IconFile3d size={40} color="var(--mantine-color-dimmed)" />
                </Dropzone.Idle>
                <Text size="sm" fw={500}>
                  Drag an .ifc file here or click to browse
                </Text>
                <Text size="xs" c="dimmed">
                  Up to 1 GB
                </Text>
              </Stack>
            </Dropzone>
          )}

          {upload.isPending && (
            <Progress value={progress} striped animated aria-label="Upload progress" />
          )}

          <Group justify="flex-end">
            <Button variant="default" onClick={handleClose} disabled={upload.isPending}>
              Cancel
            </Button>
            <Button type="submit" loading={upload.isPending} disabled={!file}>
              Upload
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
