#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    int id;
    char* title;
    int is_active;
    int total_receivers;
    int read_count;
} NotificationData;

typedef struct {
    NotificationData* notifications;
    int count;
    int total_users;
} InputData;

typedef struct {
    int total_notifications;
    int active_notifications;
    int total_users;
} BasicStats;

typedef struct {
    int id;
    char* title;
    int total_receivers;
    int read_count;
    double read_percentage;
} ProcessedStat;

typedef struct {
    BasicStats basic;
    ProcessedStat* stats;
    int stats_count;
} OutputData;

// Process all statistics
OutputData* process_stats(InputData* input) {
    OutputData* output = (OutputData*)malloc(sizeof(OutputData));
    if (!output) return NULL;
    
    // Basic stats
    output->basic.total_notifications = input->count;
    output->basic.total_users = input->total_users;
    output->basic.active_notifications = 0;
    
    for (int i = 0; i < input->count; i++) {
        if (input->notifications[i].is_active) {
            output->basic.active_notifications++;
        }
    }
    
    // Process top 5 notifications for detailed stats
    output->stats_count = (input->count > 5) ? 5 : input->count;
    output->stats = (ProcessedStat*)malloc(output->stats_count * sizeof(ProcessedStat));
    if (!output->stats) {
        free(output);
        return NULL;
    }
    
    for (int i = 0; i < output->stats_count; i++) {
        NotificationData* in = &input->notifications[i];
        ProcessedStat* out = &output->stats[i];
        
        out->id = in->id;
        out->title = strdup(in->title);
        out->total_receivers = in->total_receivers;
        out->read_count = in->read_count;
        
        if (in->total_receivers > 0) {
            out->read_percentage = (double)in->read_count / in->total_receivers * 100.0;
        } else {
            out->read_percentage = 0.0;
        }
    }
    
    return output;
}

// Free memory functions
void free_input_data(InputData* input) {
    if (input && input->notifications) {
        for (int i = 0; i < input->count; i++) {
            if (input->notifications[i].title) {
                free(input->notifications[i].title);
            }
        }
        free(input->notifications);
    }
}

void free_output_data(OutputData* output) {
    if (output) {
        if (output->stats) {
            for (int i = 0; i < output->stats_count; i++) {
                if (output->stats[i].title) {
                    free(output->stats[i].title);
                }
            }
            free(output->stats);
        }
        free(output);
    }
}